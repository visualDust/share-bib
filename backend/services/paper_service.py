from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models import Collection, CollectionPaper, CollectionPermission, Paper
from services.permission_service import check_collection_permission

_PAPER_COPY_FIELDS = (
    "title",
    "authors",
    "venue",
    "year",
    "abstract",
    "summary",
    "status",
    "bibtex_key",
    "arxiv_id",
    "doi",
    "url_arxiv",
    "url_pdf",
    "url_code",
    "url_project",
    "tags",
)


def accessible_collection_ids(user_id: str):
    """Return a SELECT for collections visible to an authenticated user."""
    explicit = select(CollectionPermission.collection_id).where(
        CollectionPermission.user_id == user_id,
        CollectionPermission.permission.in_(("view", "edit")),
    )
    return select(Collection.id).where(
        or_(
            Collection.created_by == user_id,
            Collection.visibility.in_(("public", "public_editable")),
            Collection.id.in_(explicit),
        )
    )


def accessible_paper_ids(user_id: str):
    """Return a SELECT for papers referenced by any visible collection."""
    return (
        select(CollectionPaper.paper_id)
        .where(CollectionPaper.collection_id.in_(accessible_collection_ids(user_id)))
        .distinct()
    )


def check_paper_permission(
    db: Session,
    user_id: str,
    paper_id: str,
    required_permission: str = "view",
) -> bool:
    """Check a paper through the permissions of collections that reference it."""
    collection_ids = (
        db.query(CollectionPaper.collection_id)
        .filter(CollectionPaper.paper_id == paper_id)
        .all()
    )
    return any(
        check_collection_permission(db, user_id, collection_id, required_permission)
        for (collection_id,) in collection_ids
    )


def update_paper_for_collection(
    db: Session,
    paper: Paper,
    collection_id: str,
    updates: dict,
) -> Paper:
    """Update a paper without mutating other collections.

    Papers are currently shared rows. If a paper is referenced outside the
    collection being edited, clone it and point this collection at the clone.
    This is a compatibility bridge until mutable collection-specific metadata
    can be moved onto CollectionPaper.
    """
    target_ref = (
        db.query(CollectionPaper)
        .filter(
            CollectionPaper.collection_id == collection_id,
            CollectionPaper.paper_id == paper.id,
        )
        .first()
    )
    has_external_refs = (
        db.query(CollectionPaper.id)
        .filter(
            CollectionPaper.paper_id == paper.id,
            CollectionPaper.collection_id != collection_id,
        )
        .first()
        is not None
    )

    if has_external_refs:
        values = {field: getattr(paper, field) for field in _PAPER_COPY_FIELDS}
        values.update(updates)
        clone = Paper(**values)
        db.add(clone)
        db.flush()
        if target_ref:
            target_ref.paper_id = clone.id
        return clone

    for field, value in updates.items():
        setattr(paper, field, value)
    return paper
