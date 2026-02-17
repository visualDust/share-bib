import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from database import get_db
from models import User, Collection, Paper, CollectionPaper, CollectionPermission
from schemas import (
    CollectionCreate,
    CollectionUpdate,
    CollectionOut,
    CollectionListOut,
    CollectionVisibilityUpdate,
    PermissionCreate,
    PermissionOut,
    CollectionPaperAdd,
    CollectionPaperUpdate,
    PaperReorder,
)
from schemas.collection import StatsOut, UserBrief, GroupOut, SectionOut, PaperInGroup
from services.permission_service import check_collection_permission
from services.deduplication import normalize_title
from import_module.bibtex_exporter import export_papers_to_bibtex

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("/check-id")
def check_id_available(
    id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exists = db.query(Collection).filter(Collection.id == id).first() is not None
    return {"available": not exists}


def _user_brief(user: User) -> UserBrief:
    return UserBrief(
        user_id=user.id, username=user.username, display_name=user.display_name
    )


def _collection_stats(db: Session, collection_id: str) -> StatsOut:
    cps = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [cp.paper_id for cp in cps]
    if not paper_ids:
        return StatsOut()
    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()
    accessible = sum(1 for p in papers if p.status == "accessible")
    return StatsOut(
        total=len(papers), accessible=accessible, no_access=len(papers) - accessible
    )


@router.get("", response_model=list[CollectionListOut])
def list_collections(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Collections the user can see: own, shared with them, or public
    own = db.query(Collection).filter(Collection.created_by == current_user.id)
    shared_ids = (
        db.query(CollectionPermission.collection_id)
        .filter(CollectionPermission.user_id == current_user.id)
        .subquery()
    )
    shared = db.query(Collection).filter(Collection.id.in_(shared_ids))
    public = db.query(Collection).filter(Collection.visibility == "public")
    collections = (
        own.union(shared).union(public).order_by(Collection.created_at.desc()).all()
    )

    result = []
    for c in collections:
        creator = db.query(User).filter(User.id == c.created_by).first()
        result.append(
            CollectionListOut(
                id=c.id,
                title=c.title,
                description=c.description,
                created_by=_user_brief(creator)
                if creator
                else UserBrief(user_id=c.created_by, username="unknown"),
                visibility=c.visibility,
                task_type=c.task_type,
                task_source_display=c.task_source_display,
                tags=c.tags,
                created_at=c.created_at,
                updated_at=c.updated_at,
                stats=_collection_stats(db, c.id),
            )
        )
    return result


@router.post("", response_model=CollectionListOut, status_code=status.HTTP_201_CREATED)
def create_collection(
    data: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cid = data.id or f"col-{uuid.uuid4().hex[:8]}"
    if db.query(Collection).filter(Collection.id == cid).first():
        raise HTTPException(status_code=400, detail="Collection ID already exists")
    c = Collection(
        id=cid,
        title=data.title,
        description=data.description,
        created_by=current_user.id,
        visibility=data.visibility,
        task_type=data.task_type,
        task_source=data.task_source,
        task_source_display=data.task_source_display,
        task_config=data.task_config,
        tags=data.tags,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return CollectionListOut(
        id=c.id,
        title=c.title,
        description=c.description,
        created_by=_user_brief(current_user),
        visibility=c.visibility,
        task_type=c.task_type,
        task_source_display=c.task_source_display,
        tags=c.tags,
        created_at=c.created_at,
        updated_at=c.updated_at,
        stats=StatsOut(),
    )


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "view"):
        raise HTTPException(status_code=403, detail="No permission")
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    creator = db.query(User).filter(User.id == c.created_by).first()
    perms = (
        db.query(CollectionPermission)
        .filter(CollectionPermission.collection_id == collection_id)
        .all()
    )
    perm_out = []
    for p in perms:
        u = db.query(User).filter(User.id == p.user_id).first()
        perm_out.append(
            PermissionOut(
                user_id=p.user_id,
                username=u.username if u else "unknown",
                display_name=u.display_name if u else None,
                permission=p.permission,
                granted_at=p.granted_at,
            )
        )

    # Build groups
    cps = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .order_by(CollectionPaper.display_order)
        .all()
    )
    groups_map: dict[str, dict[str, list]] = {}
    for cp in cps:
        paper = db.query(Paper).filter(Paper.id == cp.paper_id).first()
        if not paper:
            continue
        gname = cp.group_name or "未分组"
        sname = cp.section_name or "All Papers"
        if gname not in groups_map:
            groups_map[gname] = {"tag": cp.group_tag, "sections": {}}
        if sname not in groups_map[gname]["sections"]:
            groups_map[gname]["sections"][sname] = []
        groups_map[gname]["sections"][sname].append(
            PaperInGroup(
                id=paper.id,
                title=paper.title,
                authors=paper.authors,
                venue=paper.venue,
                year=paper.year,
                status=paper.status,
                urls={
                    "arxiv": paper.url_arxiv,
                    "pdf": paper.url_pdf,
                    "code": paper.url_code,
                    "project": paper.url_project,
                },
                summary=paper.summary,
                tags=paper.tags,
                added_at=cp.added_at,
            )
        )

    groups_out = []
    for gname, gdata in groups_map.items():
        sections = [
            SectionOut(name=sn, papers=sp) for sn, sp in gdata["sections"].items()
        ]
        groups_out.append(GroupOut(name=gname, tag=gdata["tag"], sections=sections))

    return CollectionOut(
        id=c.id,
        title=c.title,
        description=c.description,
        created_by=_user_brief(creator)
        if creator
        else UserBrief(user_id=c.created_by, username="unknown"),
        visibility=c.visibility,
        permissions=perm_out,
        task_type=c.task_type,
        task_source_display=c.task_source_display,
        tags=c.tags,
        created_at=c.created_at,
        updated_at=c.updated_at,
        stats=_collection_stats(db, c.id),
        groups=groups_out,
    )


@router.put("/{collection_id}", response_model=CollectionListOut)
def update_collection(
    collection_id: str,
    data: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    creator = db.query(User).filter(User.id == c.created_by).first()
    return CollectionListOut(
        id=c.id,
        title=c.title,
        description=c.description,
        created_by=_user_brief(creator)
        if creator
        else UserBrief(user_id=c.created_by, username="unknown"),
        visibility=c.visibility,
        task_type=c.task_type,
        task_source_display=c.task_source_display,
        tags=c.tags,
        created_at=c.created_at,
        updated_at=c.updated_at,
        stats=_collection_stats(db, c.id),
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")
    if c.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can delete")
    db.delete(c)
    db.commit()


@router.put("/{collection_id}/visibility")
def update_visibility(
    collection_id: str,
    data: CollectionVisibilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")
    if c.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the creator can change visibility"
        )
    c.visibility = data.visibility
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/{collection_id}/papers", status_code=status.HTTP_201_CREATED)
def add_paper_to_collection(
    collection_id: str,
    data: CollectionPaperAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    paper_id = data.paper_id
    if data.paper and not paper_id:
        p = Paper(
            title=data.paper.title,
            authors=data.paper.authors,
            venue=data.paper.venue,
            year=data.paper.year,
            abstract=data.paper.abstract,
            summary=data.paper.summary,
            status=data.paper.status,
            arxiv_id=data.paper.arxiv_id,
            doi=data.paper.doi,
            url_arxiv=data.paper.url_arxiv,
            url_pdf=data.paper.url_pdf,
            url_code=data.paper.url_code,
            url_project=data.paper.url_project,
            tags=data.paper.tags,
        )
        db.add(p)
        db.flush()
        paper_id = p.id

    if not paper_id:
        raise HTTPException(
            status_code=400, detail="Must provide paper_id or paper data"
        )

    existing = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Paper already in collection")

    cp = CollectionPaper(
        collection_id=collection_id,
        paper_id=paper_id,
        group_name=data.group_name,
        group_tag=data.group_tag,
        section_name=data.section_name,
        display_order=data.display_order,
    )
    db.add(cp)
    c.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "paper_id": paper_id}


@router.delete(
    "/{collection_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_paper_from_collection(
    collection_id: str,
    paper_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    cp = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
        .first()
    )
    if not cp:
        raise HTTPException(status_code=404, detail="Paper not in collection")
    db.delete(cp)
    db.commit()


@router.put("/{collection_id}/papers/{paper_id}")
def update_paper_in_collection(
    collection_id: str,
    paper_id: str,
    data: CollectionPaperUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    cp = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper_id,
        )
        .first()
    )
    if not cp:
        raise HTTPException(status_code=404, detail="Paper not in collection")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cp, field, value)
    db.commit()
    return {"ok": True}


@router.put("/{collection_id}/papers/reorder")
def reorder_papers(
    collection_id: str,
    data: PaperReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission")
    for item in data.paper_orders:
        cp = (
            db.query(CollectionPaper)
            .filter(
                CollectionPaper.collection_id == collection_id,
                CollectionPaper.paper_id == item["paper_id"],
            )
            .first()
        )
        if cp:
            cp.display_order = item["display_order"]
    db.commit()
    return {"ok": True}


# --- Permissions ---


@router.get("/{collection_id}/permissions", response_model=list[PermissionOut])
def list_permissions(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c or c.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the creator can manage permissions"
        )
    perms = (
        db.query(CollectionPermission)
        .filter(CollectionPermission.collection_id == collection_id)
        .all()
    )
    result = []
    for p in perms:
        u = db.query(User).filter(User.id == p.user_id).first()
        result.append(
            PermissionOut(
                user_id=p.user_id,
                username=u.username if u else "unknown",
                display_name=u.display_name if u else None,
                permission=p.permission,
                granted_at=p.granted_at,
            )
        )
    return result


@router.post(
    "/{collection_id}/permissions",
    response_model=PermissionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_permission(
    collection_id: str,
    data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c or c.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the creator can manage permissions"
        )
    perm = CollectionPermission(
        collection_id=collection_id, user_id=data.user_id, permission=data.permission
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)
    u = db.query(User).filter(User.id == data.user_id).first()
    return PermissionOut(
        user_id=perm.user_id,
        username=u.username if u else "unknown",
        display_name=u.display_name if u else None,
        permission=perm.permission,
        granted_at=perm.granted_at,
    )


@router.delete(
    "/{collection_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_permission(
    collection_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c or c.created_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the creator can manage permissions"
        )
    perm = (
        db.query(CollectionPermission)
        .filter(
            CollectionPermission.collection_id == collection_id,
            CollectionPermission.user_id == user_id,
        )
        .first()
    )
    if perm:
        db.delete(perm)
        db.commit()


# --- Export ---


@router.get("/{collection_id}/export/bibtex")
def export_collection_to_bibtex(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all papers in a collection to BibTeX format."""
    if not check_collection_permission(db, current_user.id, collection_id, "view"):
        raise HTTPException(status_code=403, detail="No permission")

    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get all papers in the collection
    cps = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [cp.paper_id for cp in cps]

    if not paper_ids:
        raise HTTPException(status_code=400, detail="Collection is empty")

    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()

    # Convert papers to dict format
    papers_data = []
    for paper in papers:
        papers_data.append(
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
        )

    # Generate BibTeX content
    bibtex_content = export_papers_to_bibtex(papers_data)

    # Return as downloadable file
    filename = f"{collection_id}.bib"
    return Response(
        content=bibtex_content,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{collection_id}/duplicates")
def find_collection_duplicates(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Find duplicate papers within a collection."""
    if not check_collection_permission(db, current_user.id, collection_id, "view"):
        raise HTTPException(status_code=403, detail="No permission")

    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get all papers in the collection
    cps = (
        db.query(CollectionPaper)
        .filter(CollectionPaper.collection_id == collection_id)
        .all()
    )
    paper_ids = [cp.paper_id for cp in cps]

    if not paper_ids:
        return {"duplicates": []}

    papers = db.query(Paper).filter(Paper.id.in_(paper_ids)).all()

    # Find duplicates using multiple strategies
    duplicates = []
    seen_pairs = set()

    for i, paper1 in enumerate(papers):
        for paper2 in papers[i + 1 :]:
            # Skip if already seen this pair
            pair_key = tuple(sorted([paper1.id, paper2.id]))
            if pair_key in seen_pairs:
                continue

            match_type = None
            match_value = None

            # Check BibTeX key
            if (
                paper1.bibtex_key
                and paper2.bibtex_key
                and paper1.bibtex_key == paper2.bibtex_key
            ):
                match_type = "bibtex_key"
                match_value = paper1.bibtex_key
            # Check arXiv ID
            elif (
                paper1.arxiv_id
                and paper2.arxiv_id
                and paper1.arxiv_id == paper2.arxiv_id
            ):
                match_type = "arxiv_id"
                match_value = paper1.arxiv_id
            # Check DOI
            elif paper1.doi and paper2.doi and paper1.doi == paper2.doi:
                match_type = "doi"
                match_value = paper1.doi
            # Check normalized title
            elif normalize_title(paper1.title) == normalize_title(paper2.title):
                match_type = "title"
                match_value = normalize_title(paper1.title)

            if match_type:
                seen_pairs.add(pair_key)
                duplicates.append(
                    {
                        "paper1_id": paper1.id,
                        "paper1_title": paper1.title,
                        "paper1_authors": paper1.authors,
                        "paper1_year": paper1.year,
                        "paper1_venue": paper1.venue,
                        "paper2_id": paper2.id,
                        "paper2_title": paper2.title,
                        "paper2_authors": paper2.authors,
                        "paper2_year": paper2.year,
                        "paper2_venue": paper2.venue,
                        "match_type": match_type,
                        "match_value": match_value,
                    }
                )

    return {"duplicates": duplicates}


@router.post("/{collection_id}/remove-duplicates")
def remove_collection_duplicates(
    collection_id: str,
    paper_ids: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove specified papers from collection (for deduplication)."""
    if not check_collection_permission(db, current_user.id, collection_id, "edit"):
        raise HTTPException(status_code=403, detail="No permission to edit collection")

    c = db.query(Collection).filter(Collection.id == collection_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Remove papers from collection
    removed = 0
    for paper_id in paper_ids:
        cp = (
            db.query(CollectionPaper)
            .filter(
                CollectionPaper.collection_id == collection_id,
                CollectionPaper.paper_id == paper_id,
            )
            .first()
        )
        if cp:
            db.delete(cp)
            removed += 1

    db.commit()
    return {"removed": removed}
