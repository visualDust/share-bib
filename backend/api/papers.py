from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from database import get_db
from models import User, Paper, CollectionPaper, UserPaperMeta
from schemas import PaperCreate, PaperUpdate, PaperOut
from schemas.user_paper_meta import UserPaperMetaOut, UserPaperMetaUpdate

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("", response_model=list[PaperOut])
def list_papers(
    q: str | None = None,
    year: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Paper)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = Paper(**data.model_dump())
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("/search", response_model=list[PaperOut])
def search_papers(
    q: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Paper)
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
    paper = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.put("/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: str,
    data: PaperUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)
    db.commit()
    db.refresh(paper)
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
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
