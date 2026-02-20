from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FetchedPaper:
    """所有数据源的统一输出格式，字段对齐 Paper 模型"""

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
        """转为可直接传给 Paper(**d) 的字典，过滤 None 值"""
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
    """描述一个配置字段"""

    key: str  # 字段名，如 "categories"
    label: str  # 显示名，如 "arXiv Categories"
    field_type: str  # "text" | "multiselect" | "number" | "keywords"
    required: bool = True
    default: Any = None
    description: str = ""
    options: list[dict] | None = None  # multiselect 的选项
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class SourceMeta:
    """数据源的元信息，用于前端展示和后端注册"""

    source_type: str  # 唯一标识，如 "arxiv_rss"
    display_name: str  # 显示名，如 "arXiv RSS"
    description: str  # 简短描述
    config_fields: list[SourceConfigField] = field(default_factory=list)
    supported_schedules: list[str] = field(
        default_factory=lambda: ["daily", "weekly", "monthly"]
    )
    rate_limit: float = 1.0  # 最小请求间隔（秒）

    def to_dict(self) -> dict:
        return asdict(self)
