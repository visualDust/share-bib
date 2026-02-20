from datetime import datetime

from pydantic import BaseModel

from schemas.user import UserBrief


class CollectionCreate(BaseModel):
    id: str | None = None
    title: str
    description: str | None = None
    visibility: str = "private"
    task_type: str = "manual_list"
    task_source: str | None = None
    task_source_display: str | None = None
    task_config: dict | None = None
    tags: list[str] | None = None


class CollectionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    task_source_display: str | None = None
    tags: list[str] | None = None
    allow_export: bool | None = None


class CollectionVisibilityUpdate(BaseModel):
    visibility: str  # private, shared, public


class StatsOut(BaseModel):
    total: int = 0
    accessible: int = 0
    no_access: int = 0


class CollectionListOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_by: UserBrief
    visibility: str
    allow_export: bool = False
    task_type: str
    task_source_display: str | None = None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    stats: StatsOut


class PaperInGroup(BaseModel):
    id: str
    title: str
    authors: list[str] | None = None
    venue: str | None = None
    year: int | None = None
    status: str
    urls: dict = {}
    summary: str | None = None
    tags: list[str] | None = None
    added_at: datetime | None = None


class SectionOut(BaseModel):
    name: str | None = None
    papers: list[PaperInGroup] = []


class GroupOut(BaseModel):
    name: str | None = None
    tag: str | None = None
    sections: list[SectionOut] = []


class PermissionOut(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    permission: str
    granted_at: datetime | None = None


class CollectionOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_by: UserBrief
    visibility: str
    allow_export: bool = False
    permissions: list[PermissionOut] = []
    task_type: str
    task_source_display: str | None = None
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime
    stats: StatsOut
    groups: list[GroupOut] = []
    current_user_permission: str | None = (
        None  # "view", "edit", or None for unauthenticated
    )


class PermissionCreate(BaseModel):
    user_id: str
    permission: str  # view or edit


class CollectionPaperAdd(BaseModel):
    paper_id: str | None = None
    paper: "PaperCreateInline | None" = None
    group_name: str | None = None
    group_tag: str | None = None
    section_name: str | None = None
    display_order: int = 0


class PaperCreateInline(BaseModel):
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


class CollectionPaperUpdate(BaseModel):
    group_name: str | None = None
    group_tag: str | None = None
    section_name: str | None = None
    display_order: int | None = None


class PaperReorder(BaseModel):
    paper_orders: list[dict]  # [{"paper_id": "...", "display_order": 0}, ...]
