"""
ShareBib Python SDK

A Python client library for interacting with the ShareBib API.
"""

__version__ = "0.1.0"

from .client import ShareBibClient
from .models import Collection, Paper

__all__ = ["ShareBibClient", "Collection", "Paper"]
