"""Pipeline module for resume parsing."""

import hashlib
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.audit.service import AuditService
from hiron.audit.utils import extract_model_changes, sanitize_audit_payload
from hiron.candidates.models import Candidate
from hiron.candidates.repository import CandidateRepository
from hiron.resumes.exceptions import (
    ResumeNotFoundError,
    ResumeParseFailedError,
)
from hiron.resumes.models import Resume
from hiron.resumes.repository import ResumeRepository


from apps.worker.src.extractor import extract_text_from_file
from apps.worker.src.parser import ResumeParser

logger = structlog.get_logger("hiron.worker.pipeline")


def _enrich_candidate_contact_info(
    candidate: Candidate,
    parsed_data: dict[str, Any],
) -> None:
    """Enrich candidate contact details from parsed data."""
    if parsed_data.get("full_name") and (
        not candidate.full_name
        or candidate.full_name in ("Placeholder Candidate", "Parsed Candidate")
    ):
        candidate.full_name = parsed_data["full_name"]
    if parsed_data.get("email") and not candidate.email:
        candidate.email = parsed_data["email"]
    if parsed_data.get("phone") and not candidate.phone:
        candidate.phone = parsed_data["phone"]
    if parsed_data.get("location") and not candidate.location:
        candidate.location = parsed_data["location"]
    if parsed_data.get("linkedin_url") and not candidate.linkedin_url:
        candidate.linkedin_url = parsed_data["linkedin_url"]
    if parsed_data.get("summary") and not candidate.summary:
        candidate.summary = parsed_data["summary"]


async def _enrich_candidate_profile(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    candidate_id: uuid.UUID,
    parsed_data: dict[str, Any],
) -> None:
    """Auto-enrich candidate profile fields from parsed resume data."""
    candidate_repo = CandidateRepository()
    candidate = await candidate_repo.get_candidate_by_id(
        session=session,
        candidate_id=candidate_id,
        tenant_id=tenant_id,
    )
    if not candidate:
        return

    _enrich_candidate_contact_info(candidate, parsed_data)

    # Skills enrichment
    extracted_skills = parsed_data.get("skills", [])
    if extracted_skills:
        existing_skills = set(candidate.skills or [])
        existing_skills.update(extracted_skills)
        candidate.skills = sorted(existing_skills)

    # Title & Company from latest experience
    experience = parsed_data.get("experience", [])
    if experience and isinstance(experience, list) and len(experience) > 0:
        first_exp = experience[0]
        if isinstance(first_exp, dict):
            if first_exp.get("title") and not candidate.current_title:
                candidate.current_title = first_exp["title"]
            if first_exp.get("company") and not candidate.current_company:
                candidate.current_company = first_exp["company"]

    await session.flush()


async def parse_resume_pipeline(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    resume_id: uuid.UUID,
) -> Resume:
    """Execute resume parsing pipeline: text extraction -> NER parsing -> DB update -> candidate auto-enrichment."""
    resume_repo = ResumeRepository()
    from hiron.storage.provider import SupabaseStorageProvider, LocalStorageProvider
    from hiron.core.config import get_settings
    settings = get_settings()

    if settings.supabase_url and settings.supabase_service_role_key:
        storage_provider = SupabaseStorageProvider(
            supabase_url=settings.supabase_url,
            supabase_service_role_key=settings.supabase_service_role_key,
            bucket_name=settings.supabase_storage_bucket,
        )
    else:
        storage_provider = LocalStorageProvider()
    
    resume = await resume_repo.get_resume_by_id(
        session=session,
        tenant_id=tenant_id,
        resume_id=resume_id,
    )
    if not resume:
        raise ResumeNotFoundError(f"Resume with ID '{resume_id}' not found")

    if resume.status in ("parsed", "failed"):
        logger.info("Skipping resume parsing: already in terminal state", status=resume.status, resume_id=str(resume_id))
        return resume

    resume_file = await resume_repo.get_resume_file_by_resume_id(
        session=session,
        tenant_id=tenant_id,
        resume_id=resume_id,
    )
    if not resume_file:
        error_msg = f"Resume file metadata missing for resume '{resume_id}'"
        await resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="failed",
            parse_error=error_msg,
        )
        raise ResumeParseFailedError(error_msg)

    await resume_repo.update_resume_status(
        session=session,
        resume=resume,
        status="processing",
    )

    # Commit processing status so it becomes durably visible to polling clients
    # before the expensive extraction and NLP parsing blocks begin.
    await session.commit()

    try:
        file_bytes = b""
        if storage_provider:
            file_bytes = await storage_provider.download_file(
                tenant_id=tenant_id,
                key=resume_file.s3_key.replace(f"{tenant_id}/", ""),
            )
        else:
            file_bytes = b"Jane Smith\njane@example.com\nSenior Python Engineer at Stripe\nSkills: Python, FastAPI, Docker, PostgreSQL"

        from fastapi.concurrency import run_in_threadpool
        raw_text = await run_in_threadpool(
            extract_text_from_file,
            file_bytes=file_bytes,
            content_type=resume_file.content_type,
            filename=resume_file.original_filename,
        )

        raw_text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        parser = ResumeParser()
        parsed_data, parse_confidence, telemetry = parser.parse(raw_text)

        updated_resume = await resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="parsed",
            parsed_data=parsed_data,
            parse_confidence=parse_confidence,
            parser_model_version=parser.model_version,
            raw_text=raw_text,
            raw_text_hash=raw_text_hash,
            parse_error="",
        )

        # Auto-enrich candidate profile
        await _enrich_candidate_profile(
            session=session,
            tenant_id=tenant_id,
            candidate_id=resume.candidate_id,
            parsed_data=parsed_data,
        )

        # Log AI usage telemetry
        if telemetry:
            try:
                # Use a SAVEPOINT so a telemetry DB failure doesn't roll back the resume parse
                async with session.begin_nested():
                    from hiron.ai_usage.repository import AIUsageRepository
                    ai_repo = AIUsageRepository()
                    await ai_repo.create_usage_log(
                        session=session,
                        tenant_id=tenant_id,
                        operation="resume_parsing",
                        model_version=telemetry["model_version"],
                        input_tokens=telemetry["input_tokens"],
                        output_tokens=telemetry["output_tokens"],
                        cost_usd=telemetry["cost_usd"],
                        latency_ms=telemetry["latency_ms"],
                        status=telemetry["status"],
                        error_type=telemetry["error_type"],
                    )
            except Exception as log_exc:
                logger.warning("Failed to write AI usage telemetry", error=str(log_exc))

        audit_service = AuditService()
        
        changes = extract_model_changes(updated_resume, "update")
        if changes:
            changes = sanitize_audit_payload(changes)
            await audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="resume_parsed",
                entity_type="resume",
                entity_id=updated_resume.id,
                actor_id=None,
                changes=changes,
            )

        await session.commit()

        # Trigger candidate embedding generation
        try:
            from hiron.core.qstash_client import qstash_publisher
            
            worker_base_url = settings.worker_url or settings.qstash_webhook_url
            if worker_base_url:
                base = worker_base_url.rstrip("/")
                webhook_url = f"{base}/api/v1/webhooks/qstash/embeddings/candidate"
                payload = {
                    "tenant_id": str(tenant_id),
                    "candidate_id": str(resume.candidate_id),
                    "model_version": "gemini-embedding-2",
                }
                dedup_id = f"embed-cand-{resume.candidate_id}-gemini-embedding-2"
                
                await qstash_publisher.publish(
                    url=webhook_url,
                    payload=payload,
                    deduplication_id=dedup_id,
                )
                logger.info("Triggered candidate embedding generation", candidate_id=str(resume.candidate_id))
            else:
                logger.warning("Skipped embedding trigger: No worker URL configured")
        except Exception as trigger_exc:
            # We explicitly catch this to preserve the successful resume parse!
            logger.error(
                "Failed to enqueue candidate embedding generation",
                error=str(trigger_exc),
                candidate_id=str(resume.candidate_id)
            )

        logger.info(
            "Resume parsed successfully",
            tenant_id=str(tenant_id),
            resume_id=str(resume_id),
            confidence=parse_confidence,
        )
        return updated_resume

    except Exception as exc:
        logger.warning(
            "Resume parsing failed",
            tenant_id=str(tenant_id),
            resume_id=str(resume_id),
            error=str(exc),
        )
        await resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="failed",
            parse_error=str(exc),
        )
        raise
