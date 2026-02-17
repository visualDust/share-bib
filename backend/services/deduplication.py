"""
Deduplication service for paper imports.

Provides duplicate detection and information tracking for BibTeX imports.
"""

import re
from enum import Enum
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Paper


class DuplicateMatchType(str, Enum):
    """Type of match used to identify a duplicate paper."""

    BIBTEX_KEY = "bibtex_key"
    ARXIV_ID = "arxiv_id"
    DOI = "doi"
    TITLE = "title"


class DuplicateInfo(BaseModel):
    """Information about a detected duplicate paper."""

    entry_id: str  # BibTeX entry ID from import file
    new_title: str
    existing_paper_id: str
    existing_title: str
    match_type: DuplicateMatchType
    match_value: str  # The actual value that matched (e.g., the arXiv ID)
    # Metadata for comparison
    new_authors: list[str] | None = None
    existing_authors: list[str] | None = None
    new_year: int | None = None
    existing_year: int | None = None
    new_venue: str | None = None
    existing_venue: str | None = None


def normalize_title(title: str) -> str:
    """Normalize title for fuzzy matching."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)  # Remove punctuation
    title = re.sub(r"\s+", " ", title).strip()  # Collapse whitespace
    return title


def find_duplicate_paper(
    db: Session, paper_data: dict, owner_user_id: str | None = None
) -> tuple[Paper | None, DuplicateInfo | None]:
    """
    Find duplicate paper using 4-step matching priority.

    If owner_user_id is provided, only searches within papers that belong to
    collections owned by that user (collection-scoped deduplication).
    Otherwise, searches globally across all papers.

    Returns (existing_paper, duplicate_info) or (None, None).
    """
    from models import Collection, CollectionPaper

    entry_id = paper_data.get("_entry_id", "unknown")

    # Build base query with optional owner filtering
    def get_paper_query():
        if owner_user_id:
            # Only search papers in collections owned by this user
            return (
                db.query(Paper)
                .join(CollectionPaper, CollectionPaper.paper_id == Paper.id)
                .join(Collection, Collection.id == CollectionPaper.collection_id)
                .filter(Collection.created_by == owner_user_id)
                .distinct()
            )
        else:
            # Global search
            return db.query(Paper)

    # 1. Try BibTeX key
    if paper_data.get("bibtex_key"):
        existing = (
            get_paper_query()
            .filter(Paper.bibtex_key == paper_data["bibtex_key"])
            .first()
        )
        if existing:
            info = DuplicateInfo(
                entry_id=entry_id,
                new_title=paper_data["title"],
                existing_paper_id=existing.id,
                existing_title=existing.title,
                match_type=DuplicateMatchType.BIBTEX_KEY,
                match_value=paper_data["bibtex_key"],
                new_authors=paper_data.get("authors"),
                existing_authors=existing.authors,
                new_year=paper_data.get("year"),
                existing_year=existing.year,
                new_venue=paper_data.get("venue"),
                existing_venue=existing.venue,
            )
            return existing, info

    # 2. Try arXiv ID
    if paper_data.get("arxiv_id"):
        existing = (
            get_paper_query().filter(Paper.arxiv_id == paper_data["arxiv_id"]).first()
        )
        if existing:
            info = DuplicateInfo(
                entry_id=entry_id,
                new_title=paper_data["title"],
                existing_paper_id=existing.id,
                existing_title=existing.title,
                match_type=DuplicateMatchType.ARXIV_ID,
                match_value=paper_data["arxiv_id"],
                new_authors=paper_data.get("authors"),
                existing_authors=existing.authors,
                new_year=paper_data.get("year"),
                existing_year=existing.year,
                new_venue=paper_data.get("venue"),
                existing_venue=existing.venue,
            )
            return existing, info

    # 3. Try DOI
    if paper_data.get("doi"):
        existing = get_paper_query().filter(Paper.doi == paper_data["doi"]).first()
        if existing:
            info = DuplicateInfo(
                entry_id=entry_id,
                new_title=paper_data["title"],
                existing_paper_id=existing.id,
                existing_title=existing.title,
                match_type=DuplicateMatchType.DOI,
                match_value=paper_data["doi"],
                new_authors=paper_data.get("authors"),
                existing_authors=existing.authors,
                new_year=paper_data.get("year"),
                existing_year=existing.year,
                new_venue=paper_data.get("venue"),
                existing_venue=existing.venue,
            )
            return existing, info

    # 4. Try normalized title
    normalized_title = normalize_title(paper_data["title"])
    # Query papers with owner filtering and check normalized titles in Python
    # (SQLite doesn't have good regex support for complex normalization)
    all_papers = get_paper_query().all()
    for paper in all_papers:
        if normalize_title(paper.title) == normalized_title:
            existing = paper
            break
    else:
        existing = None
    if existing:
        info = DuplicateInfo(
            entry_id=entry_id,
            new_title=paper_data["title"],
            existing_paper_id=existing.id,
            existing_title=existing.title,
            match_type=DuplicateMatchType.TITLE,
            match_value=normalized_title,
            new_authors=paper_data.get("authors"),
            existing_authors=existing.authors,
            new_year=paper_data.get("year"),
            existing_year=existing.year,
            new_venue=paper_data.get("venue"),
            existing_venue=existing.venue,
        )
        return existing, info

    return None, None
