"""Data models for ShareBib SDK"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Collection:
    """Represents a paper collection"""

    id: str
    title: str
    description: str
    visibility: str
    allow_export: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    paper_count: int

    @classmethod
    def from_dict(cls, data: dict) -> "Collection":
        """Create a Collection from API response data"""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            visibility=data["visibility"],
            allow_export=data["allow_export"],
            tags=data["tags"],
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ),
            paper_count=data["paper_count"],
        )


@dataclass
class Paper:
    """Represents a research paper"""

    id: str
    title: str
    authors: list[str]
    venue: Optional[str]
    year: Optional[int]
    abstract: Optional[str]
    summary: Optional[str]
    status: str
    arxiv_id: Optional[str]
    doi: Optional[str]
    url_arxiv: Optional[str]
    url_pdf: Optional[str]
    url_code: Optional[str]
    url_project: Optional[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        """Create a Paper from API response data"""
        return cls(
            id=data["id"],
            title=data["title"],
            authors=data["authors"],
            venue=data.get("venue"),
            year=data.get("year"),
            abstract=data.get("abstract"),
            summary=data.get("summary"),
            status=data["status"],
            arxiv_id=data.get("arxiv_id"),
            doi=data.get("doi"),
            url_arxiv=data.get("url_arxiv"),
            url_pdf=data.get("url_pdf"),
            url_code=data.get("url_code"),
            url_project=data.get("url_project"),
            tags=data["tags"],
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ),
        )
