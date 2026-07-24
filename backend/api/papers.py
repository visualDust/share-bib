from datetime import datetime, timezone

from auth.deps import get_admin_user, get_current_user
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models import Collection, CollectionPaper, Paper, User, UserPaperMeta
from schemas import PaperCreate, PaperOut, PaperUpdate
from schemas.user_paper_meta import UserPaperMetaOut, UserPaperMetaUpdate
from services.paper_service import (
    accessible_paper_ids,
    check_paper_permission,
    update_paper_for_collection,
)
from services.permission_service import check_collection_permission
from sqlalchemy import or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/papers", tags=["papers"])


def _visible_papers(db: Session, user_id: str):
    return db.query(Paper).filter(Paper.id.in_(accessible_paper_ids(user_id)))


def _get_visible_paper(db: Session, user_id: str, paper_id: str) -> Paper:
    paper = _visible_papers(db, user_id).filter(Paper.id == paper_id).first()
    if not paper:
        # Do not reveal whether a paper exists in an inaccessible collection.
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("", response_model=list[PaperOut])
def list_papers(
    q: str | None = None,
    year: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _visible_papers(db, current_user.id)
    if q:
        query = query.filter(
            or_(Paper.title.ilike(f"%{q}%"), Paper.abstract.ilike(f"%{q}%"))
        )
    if year:
        query = query.filter(Paper.year == year)
    if status_filter:
        query = query.filter(Paper.status == status_filter)
    return query.order_by(Paper.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def create_paper(
    data: PaperCreate,
    collection_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    paper = Paper(**data.model_dump())
    db.add(paper)
    db.flush()
    db.add(CollectionPaper(collection_id=collection_id, paper_id=paper.id))
    collection.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("/search", response_model=list[PaperOut])
def search_papers(
    q: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        _visible_papers(db, current_user.id)
        .filter(or_(Paper.title.ilike(f"%{q}%"), Paper.abstract.ilike(f"%{q}%")))
        .limit(limit)
        .all()
    )


@router.get("/by-arxiv/{arxiv_id}", response_model=PaperOut)
def get_by_arxiv(
    arxiv_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = (
        _visible_papers(db, current_user.id).filter(Paper.arxiv_id == arxiv_id).first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_visible_paper(db, current_user.id, paper_id)


@router.put("/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: str,
    data: PaperUpdate,
    collection_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    collection_ref = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
        .first()
    )
    if not paper or not collection_ref:
        raise HTTPException(status_code=404, detail="Paper not found in collection")

    paper = update_paper_for_collection(
        db,
        paper,
        collection_id,
        data.model_dump(exclude_unset=True),
    )
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if collection:
        collection.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(paper)
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Delete an unreferenced global row as an administrator maintenance action."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    refs = (
        db.query(CollectionPaper).filter(CollectionPaper.paper_id == paper_id).count()
    )
    if refs > 0:
        raise HTTPException(
            status_code=400, detail=f"Paper is referenced by {refs} collection(s)"
        )
    db.delete(paper)
    db.commit()


# --- User Paper Metadata ---


@router.get("/{paper_id}/meta", response_model=UserPaperMetaOut)
def get_paper_meta(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_paper_permission(db, current_user.id, paper_id, "view"):
        raise HTTPException(status_code=404, detail="Paper not found")
    meta = (
        db.query(UserPaperMeta)
        .filter(
            UserPaperMeta.user_id == current_user.id,
            UserPaperMeta.paper_id == paper_id,
        )
        .first()
    )
    if not meta:
        return UserPaperMetaOut(paper_id=paper_id)
    return meta


@router.put("/{paper_id}/meta", response_model=UserPaperMetaOut)
def update_paper_meta(
    paper_id: str,
    data: UserPaperMetaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_paper_permission(db, current_user.id, paper_id, "view"):
        raise HTTPException(status_code=404, detail="Paper not found")
    meta = (
        db.query(UserPaperMeta)
        .filter(
            UserPaperMeta.user_id == current_user.id,
            UserPaperMeta.paper_id == paper_id,
        )
        .first()
    )
    if not meta:
        meta = UserPaperMeta(user_id=current_user.id, paper_id=paper_id)
        db.add(meta)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(meta, field, value)
    db.commit()
    db.refresh(meta)
    return meta
