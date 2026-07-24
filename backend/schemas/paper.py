from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PaperCreate(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    authors: list[str] | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    summary: str | None = None
    status: Literal["accessible", "no_access"] = "no_access"
    arxiv_id: str | None = None
    doi: str | None = None
    url_arxiv: str | None = None
    url_pdf: str | None = None
    url_code: str | None = None
    url_project: str | None = None
    tags: list[str] | None = None


class PaperUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=1000)
    authors: list[str] | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    summary: str | None = None
    status: Literal["accessible", "no_access"] | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    url_arxiv: str | None = None
    url_pdf: str | None = None
    url_code: str | None = None
    url_project: str | None = None
    tags: list[str] | None = None


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list[str] | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    summary: str | None = None
    status: str
    arxiv_id: str | None = None
    doi: str | None = None
    url_arxiv: str | None = None
    url_pdf: str | None = None
    url_code: str | None = None
    url_project: str | None = None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaperSearch(BaseModel):
    q: str | None = None
    tags: list[str] | None = None
    year: int | None = None
    status: str | None = None
    limit: int = 50
    offset: int = 0
