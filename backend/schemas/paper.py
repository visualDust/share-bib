from datetime import datetime

from pydantic import BaseModel


class PaperCreate(BaseModel):
    title: str
    authors: list[str] | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    summary: str | None = None
    status: str = "no_access"
    arxiv_id: str | None = None
    doi: str | None = None
    url_arxiv: str | None = None
    url_pdf: str | None = None
    url_code: str | None = None
    url_project: str | None = None
    tags: list[str] | None = None


class PaperUpdate(BaseModel):
    title: str | None = None
    authors: list[str] | None = None
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    summary: str | None = None
    status: str | None = None
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
