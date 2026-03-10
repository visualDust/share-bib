"""Custom exceptions for the ShareBib SDK and CLI."""

from typing import Any


class ShareBibError(Exception):
    """Base exception for ShareBib SDK errors."""


class ShareBibConfigError(ShareBibError):
    """Raised when SDK configuration is missing or invalid."""


class ShareBibAPIError(ShareBibError):
    """Raised when the ShareBib API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
