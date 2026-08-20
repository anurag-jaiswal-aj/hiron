from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.scores.repository import ScoreRepository
from hiron.tasks.schemas import TaskProgress, TaskStatusData, TaskStatusResponse
from hiron.users.models import User

router = APIRouter(tags=["Tasks"])


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Task Status (TASK-1)",
)
async def get_task_status(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
) -> TaskStatusResponse:
    """Poll for completion of async operations per API Contract §TASK-1."""

    # Currently only supports BatchScoreJob polling in the new serverless architecture
    import uuid

    tenant_id = current_user.tenant_id
    api_status = "pending"
    progress = None

    try:
        task_uuid = uuid.UUID(task_id)
        repo = ScoreRepository()
        batch_job = await repo.get_batch_score_job(
            session=session, tenant_id=tenant_id, batch_job_id=task_id
        )

        if batch_job:
            # Map BatchScoreJob states to TASK-1 states
            if batch_job.status == "pending":
                api_status = "pending"
            elif batch_job.status == "processing":
                api_status = "progress"
                total = batch_job.queued_count or 1
                current = batch_job.completed_count + batch_job.failed_count
                percent = (current / total) * 100.0 if total > 0 else 0.0
                progress = TaskProgress(current=current, total=total, percent=percent)
            elif batch_job.status == "completed":
                api_status = "completed"
                progress = TaskProgress(
                    current=batch_job.queued_count, total=batch_job.queued_count, percent=100.0
                )
            elif batch_job.status == "failed":
                api_status = "failed"
        else:
            # Fallback for unknown tasks - return pending so UI doesn't crash,
            # or could return 404. We will return 404.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )

    except ValueError:
        # Not a valid UUID, so not a BatchScoreJob.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return TaskStatusResponse(
        data=TaskStatusData(
            task_id=task_id,
            status=api_status,
            progress=progress,
        )
    )
