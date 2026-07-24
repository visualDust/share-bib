"""ShareBib Python SDK."""

from ._version import __version__

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
    "__version__",
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
