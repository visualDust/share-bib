"""
SDK API endpoints - supports both JWT and API key authentication.
These endpoints are designed for programmatic access via the Python SDK.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from auth.deps import get_current_user, get_user_from_api_key
from database import get_db
from import_module.bibtex_exporter import export_papers_to_bibtex
from models import User, Collection, Paper, CollectionPaper, CollectionPermission
from services.permission_service import check_collection_permission

router = APIRouter(prefix="/api/sdk", tags=["sdk"])


# Pydantic models for SDK API
class PaperCreate(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    year: int | None = None
    abstract: str | None = None
    summary: str | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    url_arxiv: str | None = None
    url_pdf: str | None = None
    url_code: str | None = None
    url_project: str | None = None
    tags: list[str] = Field(default_factory=list)


class PaperOut(BaseModel):
    id: str
    title: str
    authors: list[str]
    venue: str | None
    year: int | None
    abstract: str | None
    summary: str | None
    status: str
    arxiv_id: str | None
    doi: str | None
    url_arxiv: str | None
    url_pdf: str | None
    url_code: str | None
    url_project: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class CollectionCreate(BaseModel):
    id: str | None = None
    title: str
    description: str = ""
    visibility: str = "private"
    tags: list[str] = Field(default_factory=list)


class CollectionOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    visibility: str
    allow_export: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    paper_count: int


class CollectionPaperAdd(BaseModel):
    paper_id: str
    group_name: str | None = None
    section_name: str | None = None


class CurrentUserOut(BaseModel):
    id: str
    username: str
    email: str | None
    display_name: str | None
    is_active: bool
    owned_collection_count: int
    accessible_collection_count: int


class UserSearchOut(BaseModel):
    id: str
    username: str
    display_name: str | None = None


class PermissionCreate(BaseModel):
    user_id: str
    permission: str


class PermissionOut(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    permission: str
    granted_at: datetime | None = None


# Helper to get user from either JWT or API key
async def get_sdk_user(
    jwt_user: Annotated[User | None, Depends(get_current_user)] = None,
    api_key_user: Annotated[User | None, Depends(get_user_from_api_key)] = None,
) -> User:
    """Get user from either JWT token or API key."""
    # Try API key first, then JWT
    user = api_key_user or jwt_user
    if not user:
        raise HTTPException(401, "Authentication required")
    return user


def _shared_collection_ids_subquery(user_id: str):
    return select(CollectionPermission.collection_id).filter(
        CollectionPermission.user_id == user_id
    )


def _accessible_collection_ids_subquery(user_id: str):
    shared_ids = _shared_collection_ids_subquery(user_id)
    return select(Collection.id).filter(
        or_(
            Collection.created_by == user_id,
            Collection.visibility.in_(["public", "public_editable"]),
            Collection.id.in_(shared_ids),
        )
    )


def _paper_to_out(paper: Paper) -> PaperOut:
    return PaperOut(
        id=paper.id,
        title=paper.title,
        authors=paper.authors or [],
        venue=paper.venue,
        year=paper.year,
        abstract=paper.abstract,
        summary=paper.summary,
        status=paper.status,
        arxiv_id=paper.arxiv_id,
        doi=paper.doi,
        url_arxiv=paper.url_arxiv,
        url_pdf=paper.url_pdf,
        url_code=paper.url_code,
        url_project=paper.url_project,
        tags=paper.tags or [],
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


def _collection_to_out(db: Session, collection: Collection) -> CollectionOut:
    paper_count = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection.id)
        .count()
    )
    return CollectionOut(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        visibility=collection.visibility,
        allow_export=collection.allow_export,
        tags=collection.tags or [],
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        paper_count=paper_count,
    )


def _require_collection_owner(
    db: Session, collection_id: str, user_id: str
) -> Collection:
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")
    if collection.created_by != user_id:
        raise HTTPException(403, "Only the owner can manage permissions")
    return collection


def _collapse_permissions(
    permissions: list[CollectionPermission],
) -> list[CollectionPermission]:
    by_user_id: dict[str, CollectionPermission] = {}
    for permission in permissions:
        existing = by_user_id.get(permission.user_id)
        if existing is None:
            by_user_id[permission.user_id] = permission
            continue
        if existing.permission != "edit" and permission.permission == "edit":
            by_user_id[permission.user_id] = permission
    return list(by_user_id.values())


def _permission_to_out(db: Session, permission: CollectionPermission) -> PermissionOut:
    target_user = db.query(User).filter(User.id == permission.user_id).first()
    return PermissionOut(
        user_id=permission.user_id,
        username=target_user.username if target_user else "unknown",
        display_name=target_user.display_name if target_user else None,
        permission=permission.permission,
        granted_at=permission.granted_at,
    )


@router.get("/me")
def get_current_sdk_user(
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> CurrentUserOut:
    """Get information about the current SDK user."""
    accessible_collection_count = (
        db.query(Collection)
        .filter(Collection.id.in_(_accessible_collection_ids_subquery(user.id)))
        .count()
    )
    owned_collection_count = (
        db.query(Collection).filter(Collection.created_by == user.id).count()
    )

    return CurrentUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        owned_collection_count=owned_collection_count,
        accessible_collection_count=accessible_collection_count,
    )


@router.get("/users/search")
def search_users(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> list[UserSearchOut]:
    """Search users by username for sharing workflows."""
    users = (
        db.query(User)
        .filter(User.username.ilike(f"%{q}%"), User.id != user.id)
        .limit(limit)
        .all()
    )
    return [
        UserSearchOut(
            id=matched_user.id,
            username=matched_user.username,
            display_name=matched_user.display_name,
        )
        for matched_user in users
    ]


# Collections endpoints
@router.get("/collections")
def list_collections(
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> list[CollectionOut]:
    """List all collections accessible by the user."""
    collections = (
        db.query(Collection)
        .filter(Collection.id.in_(_accessible_collection_ids_subquery(user.id)))
        .order_by(Collection.created_at.desc())
        .all()
    )
    return [_collection_to_out(db, collection) for collection in collections]


@router.post("/collections")
def create_collection(
    body: CollectionCreate,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> CollectionOut:
    """Create a new collection."""
    collection_id = body.id or str(uuid.uuid4())
    if db.query(Collection).filter(Collection.id == collection_id).first():
        raise HTTPException(400, f"Collection ID '{collection_id}' already exists")

    if body.visibility not in ["private", "public", "public_editable"]:
        raise HTTPException(400, "Invalid visibility value")

    collection = Collection(
        id=collection_id,
        title=body.title,
        description=body.description,
        created_by=user.id,
        visibility=body.visibility,
        tags=body.tags,
        task_type="manual",  # SDK-created collections are manual
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)

    return _collection_to_out(db, collection)


@router.get("/collections/{collection_id}")
def get_collection(
    collection_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> CollectionOut:
    """Get a collection by ID."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")

    if not check_collection_permission(db, user.id, collection_id, "view"):
        raise HTTPException(403, "Access denied")

    return _collection_to_out(db, collection)


@router.get("/collections/{collection_id}/permissions")
def list_collection_permissions(
    collection_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> list[PermissionOut]:
    """List effective sharing permissions for a collection."""
    _require_collection_owner(db, collection_id, user.id)
    permissions = (
        db.query(CollectionPermission)
        .filter(CollectionPermission.collection_id == collection_id)
        .all()
    )
    collapsed_permissions = _collapse_permissions(permissions)
    return [
        _permission_to_out(db, permission)
        for permission in sorted(collapsed_permissions, key=lambda item: item.user_id)
    ]


@router.post("/collections/{collection_id}/permissions")
def add_collection_permission(
    collection_id: str,
    body: PermissionCreate,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> PermissionOut:
    """Grant or replace a user's permission on a collection."""
    _require_collection_owner(db, collection_id, user.id)

    if body.permission not in {"view", "edit"}:
        raise HTTPException(400, "Invalid permission value")

    target_user = db.query(User).filter(User.id == body.user_id).first()
    if not target_user:
        raise HTTPException(404, "User not found")

    db.query(CollectionPermission).filter(
        CollectionPermission.collection_id == collection_id,
        CollectionPermission.user_id == body.user_id,
    ).delete(synchronize_session=False)

    permission = CollectionPermission(
        collection_id=collection_id,
        user_id=body.user_id,
        permission=body.permission,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)

    return _permission_to_out(db, permission)


@router.delete("/collections/{collection_id}/permissions/{target_user_id}")
def remove_collection_permission(
    collection_id: str,
    target_user_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
):
    """Remove all explicit permissions for a user on a collection."""
    _require_collection_owner(db, collection_id, user.id)

    db.query(CollectionPermission).filter(
        CollectionPermission.collection_id == collection_id,
        CollectionPermission.user_id == target_user_id,
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}


@router.get("/collections/{collection_id}/export/bibtex")
def export_collection_to_bibtex(
    collection_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
):
    """Export all papers in a collection as BibTeX."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")

    if not check_collection_permission(db, user.id, collection_id, "view"):
        raise HTTPException(403, "Access denied")

    if collection.created_by != user.id and not collection.allow_export:
        raise HTTPException(403, "Export is not allowed for this collection")

    collection_papers = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [collection_paper.paper_id for collection_paper in collection_papers]
    if not paper_ids:
        raise HTTPException(400, "Collection is empty")

    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    papers_data = [
        {
            "title": paper.title,
            "authors": paper.authors,
            "venue": paper.venue,
            "year": paper.year,
            "abstract": paper.abstract,
            "summary": paper.summary,
            "status": paper.status,
            "arxiv_id": paper.arxiv_id,
            "doi": paper.doi,
            "url_arxiv": paper.url_arxiv,
            "url_pdf": paper.url_pdf,
            "url_code": paper.url_code,
            "url_project": paper.url_project,
            "tags": paper.tags,
        }
        for paper in papers
    ]
    bibtex_content = export_papers_to_bibtex(papers_data)
    filename = f"{collection_id}.bib"

    return Response(
        content=bibtex_content,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
):
    """Delete a collection."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")

    if collection.created_by != user.id:
        raise HTTPException(403, "Only the owner can delete this collection")

    db.delete(collection)
    db.commit()
    return {"ok": True}


# Papers endpoints
@router.post("/collections/{collection_id}/papers")
def add_paper_to_collection(
    collection_id: str,
    body: PaperCreate,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> PaperOut:
    """Create a new paper and add it to a collection."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")

    if not check_collection_permission(db, user.id, collection_id, "edit"):
        raise HTTPException(403, "Write permission required")

    status = "accessible" if (body.url_arxiv or body.url_pdf) else "no_access"

    paper = Paper(
        id=str(uuid.uuid4()),
        title=body.title,
        authors=body.authors,
        venue=body.venue,
        year=body.year,
        abstract=body.abstract,
        summary=body.summary,
        arxiv_id=body.arxiv_id,
        doi=body.doi,
        url_arxiv=body.url_arxiv,
        url_pdf=body.url_pdf,
        url_code=body.url_code,
        url_project=body.url_project,
        tags=body.tags,
        status=status,
    )
    db.add(paper)

    collection_paper = CollectionPaper(
        collection_id=collection_id,
        paper_id=paper.id,
    )
    db.add(collection_paper)

    db.commit()
    db.refresh(paper)

    return _paper_to_out(paper)


@router.get("/collections/{collection_id}/papers")
def list_papers_in_collection(
    collection_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> list[PaperOut]:
    """List all papers in a collection."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")

    if not check_collection_permission(db, user.id, collection_id, "view"):
        raise HTTPException(403, "Access denied")

    collection_papers = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [collection_paper.paper_id for collection_paper in collection_papers]

    if not paper_ids:
        return []

    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    return [_paper_to_out(paper) for paper in papers]


@router.get("/papers/search")
def search_papers(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    year: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> list[PaperOut]:
    """Search papers visible to the authenticated user."""
    accessible_collection_ids = _accessible_collection_ids_subquery(user.id)
    accessible_paper_ids = select(CollectionPaper.paper_id).filter(
        CollectionPaper.collection_id.in_(accessible_collection_ids)
    )

    query = db.query(Paper).filter(Paper.id.in_(accessible_paper_ids))
    query = query.filter(
        or_(Paper.title.ilike(f"%{q}%"), Paper.abstract.ilike(f"%{q}%"))
    )
    if year is not None:
        query = query.filter(Paper.year == year)
    if status_filter:
        query = query.filter(Paper.status == status_filter)

    papers = query.order_by(Paper.created_at.desc()).limit(limit).all()
    return [_paper_to_out(paper) for paper in papers]


@router.get("/papers/{paper_id}")
def get_paper(
    paper_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> PaperOut:
    """Get a paper by ID."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")

    collection_refs = (
        db.query(CollectionPaper).filter(CollectionPaper.paper_id == paper_id).all()
    )
    if collection_refs and not any(
        check_collection_permission(db, user.id, collection_ref.collection_id, "view")
        for collection_ref in collection_refs
    ):
        raise HTTPException(403, "Access denied")

    return _paper_to_out(paper)


@router.delete("/collections/{collection_id}/papers/{paper_id}")
def remove_paper_from_collection(
    collection_id: str,
    paper_id: str,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
):
    """Remove a paper from a collection."""
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(404, "Collection not found")

    if not check_collection_permission(db, user.id, collection_id, "edit"):
        raise HTTPException(403, "Write permission required")

    collection_paper = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
        .first()
    )
    if not collection_paper:
        raise HTTPException(404, "Paper not in collection")

    db.delete(collection_paper)
    db.commit()
    return {"ok": True}
