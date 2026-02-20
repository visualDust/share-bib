from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FetchedPaper:
    """Unified output format for all data sources, fields aligned with Paper model"""

    title: str
    authors: list[str] | None = None
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    url_arxiv: str | None = None
    url_pdf: str | None = None
    url_code: str | None = None
    url_project: str | None = None
    tags: list[str] | None = None
    bibtex_key: str | None = None

    def to_paper_dict(self) -> dict:
        """Convert to a dict suitable for Paper(**d), filtering out None values"""
        d = asdict(self)
        d = {k: v for k, v in d.items() if v is not None}
        # Set status based on URL availability
        if d.get("url_arxiv") or d.get("url_pdf"):
            d["status"] = "accessible"
        else:
            d["status"] = "no_access"
        return d


@dataclass
class SourceConfigField:
    """Describes a configuration field"""

    key: str  # Field name, e.g. "categories"
    label: str  # Display name, e.g. "arXiv Categories"
    field_type: str  # "text" | "multiselect" | "number" | "keywords"
    required: bool = True
    default: Any = None
    description: str = ""
    options: list[dict] | None = None  # Options for multiselect
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class SourceMeta:
    """Source metadata, used for frontend display and backend registration"""

    source_type: str  # Unique identifier, e.g. "arxiv_rss"
    display_name: str  # Display name, e.g. "arXiv RSS"
    description: str  # Short description
    config_fields: list[SourceConfigField] = field(default_factory=list)
    supported_schedules: list[str] = field(
        default_factory=lambda: ["daily", "weekly", "monthly"]
    )
    rate_limit: float = 1.0  # Minimum request interval (seconds)

    def to_dict(self) -> dict:
        return asdict(self)
