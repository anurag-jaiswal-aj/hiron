#!/usr/bin/env python3
"""Database seeding script for generating load-test data within an isolated tenant."""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
import json
import random

# Add apps/api to Python path for module resolution
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

# Import ORM models
import hiron.candidates.models
import hiron.jobs.models
import hiron.pipeline.models
import hiron.scores.models
import hiron.audit.models
import hiron.ai_usage.models
import hiron.tenants.models
import hiron.users.models

from hiron.core.database import AsyncSessionLocal, engine
from hiron.tenants.service import TenantService
from hiron.users.service import UserService
from sqlalchemy import insert, delete, select
from sqlalchemy.orm import selectinload

from hiron.candidates.models import Candidate, JobCandidate
from hiron.jobs.models import Job, PipelineStage
from hiron.pipeline.models import CandidateStageHistory
from hiron.scores.models import Score
from hiron.audit.models import AuditLog
from hiron.ai_usage.models import AIUsageLog
from hiron.tenants.models import Tenant
from hiron.users.models import User

# Load Test Config
TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_SLUG = "loadtest-tenant"
TENANT_ID = uuid.UUID("8d299395-12f7-4177-a455-46dddff8a648")
TENANT_NAME = "LoadTest Organization"
ADMIN_EMAIL = "admin@loadtest.hiron.ai"
RECRUITER_EMAILS = [f"recruiter{i}@loadtest.hiron.ai" for i in range(1, 5)]
PASSWORD = "LoadTestPassword123!"

JOB_COUNT = 20
CANDIDATE_COUNT = 10000
PIPELINE_HISTORY_COUNT = 50000
SCORE_COUNT = 50000
AI_USAGE_COUNT = 10000
AUDIT_LOG_COUNT = 10000

def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()

async def clean_loadtest_tenant(session) -> None:
    """Safely delete ONLY the load test tenant and its cascading data."""
    print("Checking for existing loadtest tenant...")
    result = await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    tenant = result.scalar_one_or_none()
    if tenant:
        print(f"Found existing loadtest tenant (ID: {tenant.id}). Cleaning up...")
        # Since Tenant cascading might not be fully configured for everything in SQLAlchemy directly,
        # we manually delete to be safe, though ON DELETE CASCADE is often on the foreign keys in the DB.
        await session.execute(delete(AIUsageLog).where(AIUsageLog.tenant_id == tenant.id))
        await session.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant.id))
        await session.execute(delete(Score).where(Score.tenant_id == tenant.id))
        await session.execute(delete(CandidateStageHistory).where(CandidateStageHistory.tenant_id == tenant.id))
        await session.execute(delete(JobCandidate).where(JobCandidate.tenant_id == tenant.id))
        await session.execute(delete(PipelineStage).where(PipelineStage.tenant_id == tenant.id))
        await session.execute(delete(Candidate).where(Candidate.tenant_id == tenant.id))
        await session.execute(delete(Job).where(Job.tenant_id == tenant.id))
        await session.execute(delete(User).where(User.tenant_id == tenant.id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant.id))
        await session.commit()
        print("Existing loadtest tenant deleted successfully.")
    else:
        print("No existing loadtest tenant found.")

async def seed_loadtest_data() -> None:
    """Seed the database with an isolated loadtest tenant."""
    tenant_service = TenantService()
    user_service = UserService()

    async with AsyncSessionLocal() as session:
        try:
            await clean_loadtest_tenant(session)

            print("Creating loadtest tenant...")
            tenant = Tenant(
                id=TENANT_ID,
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                plan="enterprise"
            )
            session.add(tenant)
            await session.flush()
            tenant_id = tenant.id
            
            print("Creating loadtest users...")
            admin_user = await user_service.create_user(
                session=session,
                tenant_id=tenant_id,
                email=ADMIN_EMAIL,
                full_name="LoadTest Admin",
                role="org_admin",
                password=PASSWORD,
            )
            
            recruiter_users = []
            for i, email in enumerate(RECRUITER_EMAILS):
                u = await user_service.create_user(
                    session=session,
                    tenant_id=tenant_id,
                    email=email,
                    full_name=f"LoadTest Recruiter {i+1}",
                    role="recruiter",
                    password=PASSWORD,
                )
                recruiter_users.append(u)
            
            users = [admin_user] + recruiter_users
            
            await session.commit()

            print(f"Generating {JOB_COUNT} Jobs and Pipeline Stages...")
            now = datetime.now(timezone.utc)
            jobs_data = []
            job_ids = []
            for i in range(JOB_COUNT):
                job_id = generate_uuid()
                job_ids.append(job_id)
                jobs_data.append({
                    "id": job_id,
                    "tenant_id": tenant_id,
                    "title": f"LoadTest Software Engineer {i}",
                    "description": "Load test generated job description.",
                    "status": "open",
                    "is_archived": False,
                    "created_by": admin_user.id,
                    "created_at": now,
                    "updated_at": now,
                    "opened_at": now,
                    "required_skills": ["Python", "Docker"],
                    "preferred_skills": ["Locust"]
                })
            await session.execute(insert(Job).values(jobs_data))
            
            stages_data = []
            stage_ids_per_job = {}
            for j_id in job_ids:
                stages = ["Applied", "Screening", "Interview", "Offer"]
                j_stages = []
                for idx, st in enumerate(stages):
                    st_id = generate_uuid()
                    j_stages.append(st_id)
                    stages_data.append({
                        "id": st_id,
                        "tenant_id": tenant_id,
                        "job_id": j_id,
                        "name": st,
                        "position": idx + 1,
                        "is_terminal": (idx == len(stages) - 1),
                        "stage_type": "hired" if idx == len(stages) - 1 else "active",
                        "created_at": now,
                        "updated_at": now,
                    })
                stage_ids_per_job[j_id] = j_stages
            await session.execute(insert(PipelineStage).values(stages_data))
            await session.commit()

            print(f"Generating {CANDIDATE_COUNT} Candidates (this may take a moment)...")
            candidates_data = []
            job_candidates_data = []
            candidate_ids = []
            job_for_candidate = {}
            job_candidate_for_candidate = {}
            
            # Batch inserts to avoid memory bloat
            BATCH_SIZE = 1000
            for i in range(CANDIDATE_COUNT):
                c_id = generate_uuid()
                jc_id = generate_uuid()
                j_id = random.choice(job_ids)
                st_id = random.choice(stage_ids_per_job[j_id])
                u_id = random.choice(users).id

                candidate_ids.append(c_id)
                job_for_candidate[c_id] = j_id
                job_candidate_for_candidate[c_id] = jc_id
                
                candidates_data.append({
                    "id": c_id,
                    "tenant_id": tenant_id,
                    "full_name": f"Test Candidate {i}",
                    "email": f"candidate{i}@loadtest.hiron.ai",
                    "source": "api",
                    "is_archived": False,
                    "created_at": now,
                    "updated_at": now,
                    "skills": ["Python", "Testing"],
                })

                job_candidates_data.append({
                    "id": jc_id,
                    "tenant_id": tenant_id,
                    "job_id": j_id,
                    "candidate_id": c_id,
                    "current_stage_id": st_id,
                    "added_by": u_id,
                    "is_shortlisted": False,
                    "is_archived": False,
                    "created_at": now,
                    "updated_at": now,
                })
                
                if len(candidates_data) >= BATCH_SIZE:
                    await session.execute(insert(Candidate).values(candidates_data))
                    await session.execute(insert(JobCandidate).values(job_candidates_data))
                    candidates_data = []
                    job_candidates_data = []
                    
            if candidates_data:
                await session.execute(insert(Candidate).values(candidates_data))
                await session.execute(insert(JobCandidate).values(job_candidates_data))
            await session.commit()

            print(f"Generating {PIPELINE_HISTORY_COUNT} Pipeline Stage Histories...")
            history_data = []
            for i in range(PIPELINE_HISTORY_COUNT):
                c_id = random.choice(candidate_ids)
                j_id = job_for_candidate[c_id]
                jc_id = job_candidate_for_candidate[c_id]
                st_id = random.choice(stage_ids_per_job[j_id])
                u_id = random.choice(users).id
                history_data.append({
                    "id": generate_uuid(),
                    "tenant_id": tenant_id,
                    "job_candidate_id": jc_id,
                    "from_stage_id": None,
                    "to_stage_id": st_id,
                    "moved_by": u_id,
                    "created_at": now,
                })
                if len(history_data) >= BATCH_SIZE:
                    await session.execute(insert(CandidateStageHistory).values(history_data))
                    history_data = []
            if history_data:
                await session.execute(insert(CandidateStageHistory).values(history_data))
            await session.commit()
            
            print(f"Generating {SCORE_COUNT} Scores...")
            scores_data = []
            seen_jc_ids = set()
            for i in range(SCORE_COUNT):
                c_id = random.choice(candidate_ids)
                jc_id = job_candidate_for_candidate[c_id]
                is_current = False
                if jc_id not in seen_jc_ids:
                    is_current = True
                    seen_jc_ids.add(jc_id)
                scores_data.append({
                    "id": generate_uuid(),
                    "tenant_id": tenant_id,
                    "job_candidate_id": jc_id,
                    "fit_score": random.randint(50, 100),
                    "confidence": 0.85,
                    "breakdown": {"technical": 90, "cultural": 80},
                    "explanation": "Loadtest generated explanation",
                    "prompt_name": "loadtest_prompt",
                    "prompt_version": "v1",
                    "model_version": "gpt-4",
                    "input_tokens": 1500,
                    "output_tokens": 300,
                    "latency_ms": 1200,
                    "is_current": is_current,
                    "created_at": now,
                })
                if len(scores_data) >= BATCH_SIZE:
                    await session.execute(insert(Score).values(scores_data))
                    scores_data = []
            if scores_data:
                await session.execute(insert(Score).values(scores_data))
            await session.commit()

            print(f"Generating {AI_USAGE_COUNT} AI Usage Logs...")
            usage_data = []
            for i in range(AI_USAGE_COUNT):
                u_id = random.choice(users).id
                usage_data.append({
                    "id": generate_uuid(),
                    "tenant_id": tenant_id,
                    "user_id": u_id,
                    "operation": "resume_parsing",
                    "model_version": "gpt-4o",
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "total_tokens": 1200,
                    "cost_usd": 0.01,
                    "latency_ms": 1500,
                    "status": "success",
                    "is_cache_hit": False,
                    "created_at": now,
                })
                if len(usage_data) >= BATCH_SIZE:
                    await session.execute(insert(AIUsageLog).values(usage_data))
                    usage_data = []
            if usage_data:
                await session.execute(insert(AIUsageLog).values(usage_data))
            await session.commit()

            print(f"Generating {AUDIT_LOG_COUNT} Audit Logs...")
            audit_data = []
            for i in range(AUDIT_LOG_COUNT):
                u_id = random.choice(users).id
                audit_data.append({
                    "id": generate_uuid(),
                    "tenant_id": tenant_id,
                    "actor_id": u_id,
                    "action": "candidate_created",
                    "entity_type": "candidate",
                    "entity_id": random.choice(candidate_ids),
                    "created_at": now,
                })
                if len(audit_data) >= BATCH_SIZE:
                    await session.execute(insert(AuditLog).values(audit_data))
                    audit_data = []
            if audit_data:
                await session.execute(insert(AuditLog).values(audit_data))
            await session.commit()

            print("✓ Load test data seeding completed successfully.")
            print(f"  Tenant ID:   {tenant_id}")
            print(f"  Admin User:  {admin_user.full_name} <{admin_user.email}>")
            print(f"  Job 0 ID:    {job_ids[0]}")

        except Exception as exc:
            await session.rollback()
            print(f"❌ Database seeding failed: {exc}", file=sys.stderr)
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_loadtest_data())
