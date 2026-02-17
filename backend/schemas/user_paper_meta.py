from datetime import datetime

from pydantic import BaseModel, Field


class UserPaperMetaOut(BaseModel):
    paper_id: str
    read_status: str = "unread"
    note: str | None = None
    rating: int | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserPaperMetaUpdate(BaseModel):
    read_status: str | None = None
    note: str | None = None
    rating: int | None = Field(None, ge=1, le=5)
