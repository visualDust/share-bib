"""Data models for the ShareBib SDK."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO-8601 datetimes returned by the API."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class CurrentUser:
    """Information about the authenticated SDK user."""

    id: str
    username: str
    email: Optional[str]
    display_name: Optional[str]
    is_active: bool
    owned_collection_count: int
    accessible_collection_count: int

    @classmethod
    def from_dict(cls, data: dict) -> "CurrentUser":
        """Create a CurrentUser from API response data."""
        return cls(
            id=data["id"],
            username=data["username"],
            email=data.get("email"),
            display_name=data.get("display_name"),
            is_active=data["is_active"],
            owned_collection_count=data["owned_collection_count"],
            accessible_collection_count=data["accessible_collection_count"],
        )


@dataclass
class UserSummary:
    """A lightweight user record for search and sharing flows."""

    id: str
    username: str
    display_name: Optional[str]

    @classmethod
    def from_dict(cls, data: dict) -> "UserSummary":
        return cls(
            id=data["id"],
            username=data["username"],
            display_name=data.get("display_name"),
        )


@dataclass
class CollectionPermissionEntry:
    """A collection sharing permission entry."""

    user_id: str
    username: str
    display_name: Optional[str]
    permission: str
    granted_at: datetime | None

    @classmethod
    def from_dict(cls, data: dict) -> "CollectionPermissionEntry":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            display_name=data.get("display_name"),
            permission=data["permission"],
            granted_at=_parse_datetime(data.get("granted_at")),
        )


@dataclass
class Collection:
    """Represents a paper collection."""

    id: str
    title: str
    description: Optional[str]
    visibility: str
    allow_export: bool
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    paper_count: int

    @classmethod
    def from_dict(cls, data: dict) -> "Collection":
        """Create a Collection from API response data."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            visibility=data["visibility"],
            allow_export=data["allow_export"],
            tags=data.get("tags") or [],
            created_at=_parse_datetime(data["created_at"]),
            updated_at=_parse_datetime(data["updated_at"]),
            paper_count=data["paper_count"],
        )


@dataclass
class Paper:
    """Represents a research paper."""

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
        """Create a Paper from API response data."""
        return cls(
            id=data["id"],
            title=data["title"],
            authors=data.get("authors") or [],
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
            tags=data.get("tags") or [],
            created_at=_parse_datetime(data["created_at"]),
            updated_at=_parse_datetime(data["updated_at"]),
        )
