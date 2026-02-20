from abc import ABC, abstractmethod
from datetime import datetime

from crawl.types import FetchedPaper, SourceMeta


class CrawlSource(ABC):
    """
    Base class for data sources. To add a new source:
    1. Subclass this class
    2. Implement meta() and fetch()
    3. Register in sources/__init__.py REGISTRY
    """

    @classmethod
    @abstractmethod
    def meta(cls) -> SourceMeta:
        """Return source metadata (config schema, display name, etc.). Pure declaration, no IO."""
        ...

    @abstractmethod
    async def fetch(
        self,
        config: dict,
        since: datetime | None,
        user_settings: dict | None = None,
    ) -> list[FetchedPaper]:
        """
        Execute a crawl.
        - config: configuration validated by validate_config
        - since: last successful crawl time, None for first run
        - user_settings: user-level settings (e.g. API key), injected by executor from DB
        - Returns: list of FetchedPaper
        - Network/parsing errors should be raised as exceptions, caught by the executor
        """
        ...

    def validate_config(self, config: dict) -> dict:
        """Validate and normalize config. Default implementation does basic validation based on meta().config_fields."""
        meta = self.meta()
        cleaned = {}
        for f in meta.config_fields:
            value = config.get(f.key, f.default)
            if f.required and value is None:
                raise ValueError(f"Missing required config: {f.key}")
            cleaned[f.key] = value
        return cleaned
