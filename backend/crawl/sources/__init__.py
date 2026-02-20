from crawl.sources.arxiv_rss import ArxivRSSSource
from crawl.sources.semantic_scholar import SemanticScholarSource
from crawl.sources.base import CrawlSource
from crawl.types import SourceMeta

# Registry: source_type -> CrawlSource instance
# To add a new source, just add a line here
REGISTRY: dict[str, CrawlSource] = {
    "arxiv_rss": ArxivRSSSource(),
    "semantic_scholar": SemanticScholarSource(),
}


def get_source(source_type: str) -> CrawlSource:
    source = REGISTRY.get(source_type)
    if not source:
        raise ValueError(f"Unknown source type: {source_type}")
    return source


def list_sources() -> list[SourceMeta]:
    """Return metadata for all registered sources, used by API and frontend"""
    return [s.meta() for s in REGISTRY.values()]
