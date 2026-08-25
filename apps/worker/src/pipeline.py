"""Pipeline module for resume parsing."""

import hashlib
import time
import uuid
from typing import Any

import structlog
from apps.worker.src.extractor import extract_text_from_file
from apps.worker.src.parser import ResumeParser, GeminiResumeParser
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


async def _log_ai_usage_telemetry(session: AsyncSession, tenant_id: uuid.UUID, telemetry: dict[str, Any] | None) -> None:
    if not telemetry:
        return
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
                is_cache_hit=False,
            )
    except Exception as log_exc:
        logger.warning("Failed to write AI usage telemetry", error=str(log_exc))

async def _parse_resume_with_gemini_fallback(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    raw_text: str,
) -> tuple[dict[str, Any], float, dict[str, Any] | None, str]:
    """Parse resume using Gemini AI with deterministic fallback."""
    if not raw_text or not raw_text.strip():
        # Empty/whitespace text -> skip Gemini, use deterministic parser which handles empty text safely
        legacy_parser = ResumeParser()
        parsed_data, parse_confidence, telemetry = legacy_parser.parse(raw_text)
        return parsed_data, parse_confidence, telemetry, legacy_parser.model_version

    gemini_parser = GeminiResumeParser()
    parser_model_version = gemini_parser.model_version
    gemini_start_time = time.time()

    try:
        parsed_data, parse_confidence, telemetry = await gemini_parser.parse_async(raw_text)
        return parsed_data, parse_confidence, telemetry, parser_model_version
    except Exception as e:
        # Capture Gemini failure telemetry
        latency_ms = int((time.time() - gemini_start_time) * 1000)
        error_type = type(e).__name__

        # Safely extract error count for ValidationErrors without logging PII
        error_details = f"{e.error_count()} validation errors" if hasattr(e, "error_count") else "API/Timeout Error"

        logger.warning(
            "Gemini parsing failed",
            error_type=error_type,
            details=error_details,
        )

        try:
            # Write Gemini failure telemetry IMMEDIATELY inside a savepoint
            async with session.begin_nested():
                from hiron.ai_usage.repository import AIUsageRepository
                ai_repo = AIUsageRepository()
                await ai_repo.create_usage_log(
                    session=session,
                    tenant_id=tenant_id,
                    operation="resume_parsing",
                    model_version=parser_model_version,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    status="error",
                    error_type=error_type,
                    is_cache_hit=False,
                )
        except Exception as log_exc:
            logger.warning("Failed to log Gemini failure telemetry", error=str(log_exc))

        from google.genai.errors import APIError
        from pydantic import ValidationError

        is_permanent_error = False
        if (isinstance(e, APIError) and e.code == 400) or isinstance(e, ValidationError):
            is_permanent_error = True

        if not is_permanent_error:
            logger.warning("Propagating transient Gemini error for QStash retry")
            raise

        logger.warning("Permanent Gemini parsing error, falling back to deterministic extraction")
        # Deterministic Fallback
        legacy_parser = ResumeParser()
        parsed_data, parse_confidence, telemetry = legacy_parser.parse(raw_text)
        return parsed_data, parse_confidence, telemetry, legacy_parser.model_version

async def _trigger_candidate_embedding(tenant_id: uuid.UUID, candidate_id: uuid.UUID) -> None:
    """Safely trigger background candidate embedding generation without failing the parse."""
    try:
        from hiron.core.config import get_settings
        settings = get_settings()
        from hiron.core.qstash_client import qstash_publisher

        worker_base_url = settings.worker_url or settings.qstash_webhook_url
        if worker_base_url:
            base = worker_base_url.rstrip("/")
            webhook_url = f"{base}/api/v1/webhooks/qstash/embeddings/candidate"
            payload = {
                "tenant_id": str(tenant_id),
                "candidate_id": str(candidate_id),
                "model_version": "gemini-embedding-2",
            }
            dedup_id = f"embed-cand-{candidate_id}-gemini-embedding-2"

            await qstash_publisher.publish(
                url=webhook_url,
                payload=payload,
                deduplication_id=dedup_id,
            )
            logger.info("Triggered candidate embedding generation", candidate_id=str(candidate_id))
        else:
            logger.warning("Skipped embedding trigger: No worker URL configured")
    except Exception as trigger_exc:
        # We explicitly catch this to preserve the successful resume parse!
        logger.error(
            "Failed to enqueue candidate embedding generation",
            error=str(trigger_exc),
            candidate_id=str(candidate_id)
        )


def _get_safe_error_message(exc: Exception) -> str:
    """Return a PII-safe error message for logging and database storage."""
    from hiron.resumes.exceptions import ResumeParseFailedError

    if isinstance(exc, ResumeParseFailedError):
        # Internally generated extraction errors are known to be safe
        return str(exc)

    try:
        from google.genai.errors import APIError
        if isinstance(exc, APIError):
            code = getattr(exc, "code", None)
            status_attr = getattr(exc, "status", None)
            if code is not None and status_attr is not None:
                return f"Gemini API error (code={code} status={status_attr})"
            if code is not None:
                return f"Gemini API error (code={code})"
            if status_attr is not None:
                return f"Gemini API error (status={status_attr})"
            return "Gemini API error"
    except ImportError:
        pass

    try:
        from pydantic import ValidationError
        if isinstance(exc, ValidationError):
            return "Resume schema validation failed"
    except ImportError:
        pass

    if isinstance(exc, TimeoutError):
        return "Resume parsing timed out"

    return f"Resume parsing failed: {type(exc).__name__}"


async def parse_resume_pipeline(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    resume_id: uuid.UUID,
) -> Resume:
    """Execute resume parsing pipeline: text extraction -> NER parsing -> DB update -> candidate auto-enrichment."""
    resume_repo = ResumeRepository()
    from hiron.core.config import get_settings
    from hiron.storage.provider import LocalStorageProvider, SupabaseStorageProvider
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
        raw_text, text_was_truncated = await run_in_threadpool(
            extract_text_from_file,
            file_bytes=file_bytes,
            content_type=resume_file.content_type,
            filename=resume_file.original_filename,
        )

        if text_was_truncated:
            logger.warning(
                "Resume text extraction was truncated to protect downstream systems",
                tenant_id=str(tenant_id),
                resume_id=str(resume_id),
                retained_chars=len(raw_text),
                truncated=True,
            )

        raw_text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # Phase B: Gemini AI Parser with deterministic fallback
        parsed_data, parse_confidence, telemetry, parser_model_version = await _parse_resume_with_gemini_fallback(
            session=session,
            tenant_id=tenant_id,
            raw_text=raw_text,
        )

        updated_resume = await resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="parsed",
            parsed_data=parsed_data,
            parse_confidence=parse_confidence,
            parser_model_version=parser_model_version,
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
        await _log_ai_usage_telemetry(session, tenant_id, telemetry)
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
        await _trigger_candidate_embedding(tenant_id, resume.candidate_id)

        logger.info(
            "Resume parsed successfully",
            tenant_id=str(tenant_id),
            resume_id=str(resume_id),
            confidence=parse_confidence,
        )
        return updated_resume

    except Exception as exc:
        safe_error = _get_safe_error_message(exc)
        logger.warning(
            "Resume parsing failed",
            tenant_id=str(tenant_id),
            resume_id=str(resume_id),
            error=safe_error,
        )
        await resume_repo.update_resume_status(
            session=session,
            resume=resume,
            status="failed",
            parse_error=safe_error,
        )
        raise
