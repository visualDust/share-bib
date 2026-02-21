"""
SDK API endpoints - supports both JWT and API key authentication.
These endpoints are designed for programmatic access via the Python SDK.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.deps import get_current_user, get_user_from_api_key
from database import get_db
from models import User, Collection, Paper, CollectionPaper
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
    description: str
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


# Collections endpoints
@router.get("/collections")
def list_collections(
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> list[CollectionOut]:
    """List all collections accessible by the user."""
    # Get collections created by user
    collections = (
        db.query(Collection)
        .filter(Collection.created_by == user.id)
        .order_by(Collection.created_at.desc())
        .all()
    )

    result = []
    for c in collections:
        paper_count = (
            db.query(CollectionPaper)
            .filter(CollectionPaper.collection_id == c.id)
            .count()
        )
        result.append(
            CollectionOut(
                id=c.id,
                title=c.title,
                description=c.description,
                visibility=c.visibility,
                allow_export=c.allow_export,
                tags=c.tags or [],
                created_at=c.created_at,
                updated_at=c.updated_at,
                paper_count=paper_count,
            )
        )
    return result


@router.post("/collections")
def create_collection(
    body: CollectionCreate,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
) -> CollectionOut:
    """Create a new collection."""
    # Check if custom ID is provided and available
    collection_id = body.id or str(uuid.uuid4())
    if db.query(Collection).filter(Collection.id == collection_id).first():
        raise HTTPException(400, f"Collection ID '{collection_id}' already exists")

    # Validate visibility
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

    return CollectionOut(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        visibility=collection.visibility,
        allow_export=collection.allow_export,
        tags=collection.tags or [],
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        paper_count=0,
    )


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

    # Check permission
    if not check_collection_permission(db, user.id, collection_id, "view"):
        raise HTTPException(403, "Access denied")

    paper_count = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
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

    # Only owner can delete
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

    # Check write permission
    if not check_collection_permission(db, user.id, collection_id, "edit"):
        raise HTTPException(403, "Write permission required")

    # Create paper
    # Determine status based on whether PDF/arXiv links are available
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

    # Add to collection
    cp = CollectionPaper(
        collection_id=collection_id,
        paper_id=paper.id,
    )
    db.add(cp)

    db.commit()
    db.refresh(paper)

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

    # Check read permission
    if not check_collection_permission(db, user.id, collection_id, "view"):
        raise HTTPException(403, "Access denied")

    # Get papers
    cps = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [cp.paper_id for cp in cps]

    if not paper_ids:
        return []

    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()

    return [
        PaperOut(
            id=p.id,
            title=p.title,
            authors=p.authors or [],
            venue=p.venue,
            year=p.year,
            abstract=p.abstract,
            summary=p.summary,
            status=p.status,
            arxiv_id=p.arxiv_id,
            doi=p.doi,
            url_arxiv=p.url_arxiv,
            url_pdf=p.url_pdf,
            url_code=p.url_code,
            url_project=p.url_project,
            tags=p.tags or [],
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in papers
    ]


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

    # Check if user has access to this paper through any collection
    cp = db.query(CollectionPaper).filter(CollectionPaper.paper_id == paper_id).first()
    if cp:
        if not check_collection_permission(db, user.id, cp.collection_id, "view"):
            raise HTTPException(403, "Access denied")

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

    # Check write permission
    if not check_collection_permission(db, user.id, collection_id, "edit"):
        raise HTTPException(403, "Write permission required")

    cp = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
        .first()
    )
    if not cp:
        raise HTTPException(404, "Paper not in collection")

    db.delete(cp)
    db.commit()
    return {"ok": True}
