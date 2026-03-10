"""ShareBib Python SDK."""

__version__ = "0.1.0"

from .client import ShareBibClient
from .exceptions import ShareBibAPIError, ShareBibConfigError, ShareBibError
from .models import (
    Collection,
    CollectionPermissionEntry,
    CurrentUser,
    Paper,
    UserSummary,
)

__all__ = [
    "ShareBibClient",
    "ShareBibError",
    "ShareBibConfigError",
    "ShareBibAPIError",
    "CurrentUser",
    "UserSummary",
    "CollectionPermissionEntry",
    "Collection",
    "Paper",
]
