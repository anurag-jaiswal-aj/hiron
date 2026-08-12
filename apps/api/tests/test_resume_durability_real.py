import asyncio
import typing
import uuid

import pytest
from sqlalchemy import text

from hiron.core.database import AsyncSessionLocal, check_database_connection
from hiron.resumes.models import Resume, ResumeFile
from hiron.resumes.service import ResumeService


@pytest.mark.asyncio
async def test_processing_durability_concurrent_visibility() -> None:
    """Proves processing status is durably committed before parsing blocks."""
    # Test against real database
    is_healthy, _ = await check_database_connection()
    if not is_healthy:
        pytest.skip("Test requires active Postgres database")

    # 1. Setup real resume in DB directly
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        # Create minimal tenant, candidate and resume
        from hiron.tenants.models import Tenant
        tenant = Tenant(id=tenant_id, name="Test Tenant", slug=f"test-tenant-{tenant_id}")
        session.add(tenant)

        from hiron.candidates.models import Candidate
        candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="Test")
        session.add(candidate)

        resume = Resume(
            id=resume_id,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            status="pending"
        )
        session.add(resume)

        resume_file = ResumeFile(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            resume_id=resume_id,
            s3_bucket="test",
            s3_key=f"{tenant_id}/{resume_id}/file.pdf",
            original_filename="file.pdf",
            content_type="application/pdf",
            file_size_bytes=100,
            checksum_sha256="hash"
        )
        session.add(resume_file)
        await session.commit()

    # 2. Patch extractor to simulate expensive extraction (pause execution)
    from unittest.mock import patch

    # We will use Events to orchestrate the concurrency robustly
    extraction_started = asyncio.Event()
    check_finished = asyncio.Event()

    observed_status = None

    try:
        async def run_pipeline() -> None:
            async with AsyncSessionLocal() as session:
                service = ResumeService()

                loop = asyncio.get_running_loop()
                with patch("hiron.resumes.service.extract_text_from_file") as mock_ext:
                    def side_effect(*_a: typing.Any, **__kw: typing.Any) -> typing.Any:
                        # Notify the independent reader that extraction has started
                        loop.call_soon_threadsafe(extraction_started.set)
                        # Wait for the independent reader to finish its check before proceeding
                        import time
                        start_time = time.time()
                        while not check_finished.is_set() and time.time() - start_time < 2.0:
                            time.sleep(0.01)
                        return "Fake text"
                    mock_ext.side_effect = side_effect

                    # Run pipeline (bounded by a reasonable timeout)
                    await asyncio.wait_for(
                        service.parse_resume_pipeline(session, tenant_id, resume_id),
                        timeout=15.0
                    )
                    await session.commit()

        async def concurrent_reader() -> None:
            try:
                # Wait until extraction starts
                await asyncio.wait_for(extraction_started.wait(), timeout=10.0)

                # Independent session reads the status
                async with AsyncSessionLocal() as session:
                    from hiron.resumes.repository import ResumeRepository
                    repo = ResumeRepository()
                    r = await repo.get_resume_by_id(session, tenant_id, resume_id)
                    nonlocal observed_status
                    observed_status = r.status if r else None
            finally:
                # Always signal that the check finished so the pipeline can unblock
                check_finished.set()

        # Run them concurrently
        await asyncio.gather(run_pipeline(), concurrent_reader())

        # 3. Assertions
        # The concurrent reader MUST have observed "processing"
        assert observed_status == "processing", "Processing status was not durably committed before extraction"

        # Verify final state is parsed
        async with AsyncSessionLocal() as session:
            from hiron.resumes.repository import ResumeRepository
            repo = ResumeRepository()
            r = await repo.get_resume_by_id(session, tenant_id, resume_id)
            if r is not None:
                assert r.status == "parsed"

    finally:
        # 4. Deterministic database cleanup
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM resume_files WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await session.execute(text("DELETE FROM resumes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await session.execute(text("DELETE FROM candidates WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await session.execute(text("DELETE FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant_id})
            await session.commit()

def test_celery_event_loop_lifecycle_sync() -> None:
    """Proves that sequential Celery task executions do not crash with event loop errors."""
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    resume_id_1 = uuid.uuid4()
    resume_id_2 = uuid.uuid4()

    async def setup_db() -> bool:
        from hiron.core.database import engine
        await engine.dispose()
        is_healthy, _ = await check_database_connection()
        if not is_healthy:
            return False

        try:
            async with AsyncSessionLocal() as session:
                from hiron.tenants.models import Tenant
                tenant = Tenant(id=tenant_id, name="Test Tenant Lifecycle", slug=f"lifecycle-{tenant_id}")
                session.add(tenant)

                from hiron.candidates.models import Candidate
                candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="Test")
                session.add(candidate)

                from hiron.resumes.models import Resume, ResumeFile
                for rid in (resume_id_1, resume_id_2):
                    resume = Resume(
                        id=rid,
                        tenant_id=tenant_id,
                        candidate_id=candidate_id,
                        status="pending"
                    )
                    session.add(resume)
                    resume_file = ResumeFile(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        resume_id=rid,
                        s3_bucket="test",
                        s3_key=f"{tenant_id}/{rid}/file.pdf",
                        original_filename="file.pdf",
                        content_type="application/pdf",
                        file_size_bytes=100,
                        checksum_sha256=f"hash_{rid}"
                    )
                    session.add(resume_file)
                await session.commit()
            return True
        finally:
            from hiron.core.database import engine
            await engine.dispose()
    from asgiref.sync import async_to_sync
    is_healthy = async_to_sync(setup_db)()
    if not is_healthy:
        pytest.skip("Test requires active Postgres database")

    try:
        from unittest.mock import patch
        with patch("hiron.resumes.service.extract_text_from_file", return_value="Fake text"):
            # Import the celery task wrapper
            from hiron.resumes.tasks import parse_resume
            # Execute first task. This will create the persistent thread-local event loop via async_to_sync.
            res1 = parse_resume(str(tenant_id), str(resume_id_1))
            assert res1["status"] == "success"
            assert res1["resume_id"] == str(resume_id_1)
            # Execute second task. This must reuse the loop and NOT crash.
            res2 = parse_resume(str(tenant_id), str(resume_id_2))
            assert res2["status"] == "success"
            assert res2["resume_id"] == str(resume_id_2)

    finally:
        async def cleanup_db() -> None:
            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(text("DELETE FROM resume_files WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await session.execute(text("DELETE FROM resumes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await session.execute(text("DELETE FROM candidates WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
                    await session.execute(text("DELETE FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant_id})
                    await session.commit()
            finally:
                from hiron.core.database import engine
                await engine.dispose()
        async_to_sync(cleanup_db)()
