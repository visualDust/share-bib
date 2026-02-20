from crawl.sources.arxiv_rss import ArxivRSSSource
from crawl.sources.base import CrawlSource
from crawl.types import SourceMeta

# 注册表：source_type -> CrawlSource 实例
# 加新源只需在这里加一行
REGISTRY: dict[str, CrawlSource] = {
    "arxiv_rss": ArxivRSSSource(),
}


def get_source(source_type: str) -> CrawlSource:
    source = REGISTRY.get(source_type)
    if not source:
        raise ValueError(f"Unknown source type: {source_type}")
    return source


def list_sources() -> list[SourceMeta]:
    """返回所有已注册源的元信息，供 API 和前端使用"""
    return [s.meta() for s in REGISTRY.values()]
