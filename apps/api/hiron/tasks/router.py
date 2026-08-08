from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from hiron.auth.dependencies import get_current_user
from hiron.core.celery import celery_app
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
) -> TaskStatusResponse:
    """Poll for completion of async operations per API Contract §TASK-1."""

    # 1. Tenant Isolation verification
    # Format of secure task ID: <prefix>-<tenant_id>-<uuid>
    # e.g., batch-1234-abcd-5678-efgh-...
    tenant_str = str(current_user.tenant_id)
    if tenant_str not in task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    result = celery_app.AsyncResult(task_id)

    # Map Celery states to TASK-1 states
    state = result.state
    api_status = "pending"
    progress = None

    if state == "PENDING":
        api_status = "pending"
    elif state == "PROGRESS":
        api_status = "progress"
        meta = result.info or {}
        current = meta.get("current", 0)
        total = meta.get("total", 1)
        percent = meta.get("percent", 0.0)
        progress = TaskProgress(current=current, total=total, percent=percent)
    elif state == "SUCCESS":
        api_status = "completed"
        progress = TaskProgress(current=1, total=1, percent=100.0)
    elif state == "FAILURE":
        api_status = "failed"
    else:
        api_status = "pending"

    return TaskStatusResponse(
        data=TaskStatusData(
            task_id=task_id,
            status=api_status,
            progress=progress,
        )
    )
