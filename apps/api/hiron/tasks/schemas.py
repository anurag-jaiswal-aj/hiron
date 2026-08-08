from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from hiron.common.schemas import HironBaseModel


class TaskProgress(BaseModel):
    current: int = Field(...)
    total: int = Field(...)
    percent: float = Field(...)

class TaskStatusData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(..., serialization_alias="taskId")
    status: str = Field(...)
    progress: TaskProgress | None = Field(default=None)
    created_at: datetime | None = Field(default=None, serialization_alias="createdAt")

class TaskStatusResponse(HironBaseModel):
    data: TaskStatusData = Field(...)
