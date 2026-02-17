from datetime import datetime

from pydantic import BaseModel


class ImportTaskOut(BaseModel):
    task_id: str
    status: str
    progress: dict | None = None
    result: dict | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
