"""ShareBib API client."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import requests

from .config import ConfigManager, normalize_base_url, validate_api_key
from .exceptions import ShareBibAPIError, ShareBibConfigError
from .models import (
    Collection,
    CollectionPermissionEntry,
    CurrentUser,
    Paper,
    UserSummary,
)


class ShareBibClient:
    """Client for interacting with the ShareBib SDK API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        config_path: str | Path | None = None,
    ):
        config = ConfigManager.load_config(
            Path(config_path) if config_path is not None else None,
            require_api_key=False,
        )

        resolved_api_key = api_key or config.get("api_key")
        if not isinstance(resolved_api_key, str) or not resolved_api_key:
            raise ShareBibConfigError(
                "API key not found. Set SHAREBIB_API_KEY or provide api_key explicitly."
            )
        validate_api_key(resolved_api_key)

        resolved_base_url = base_url or config.get("base_url")
        if not isinstance(resolved_base_url, str) or not resolved_base_url:
            resolved_base_url = ConfigManager.DEFAULT_BASE_URL

        resolved_timeout = timeout if timeout is not None else config.get("timeout")
        if not isinstance(resolved_timeout, int) or resolved_timeout <= 0:
            raise ShareBibConfigError("Timeout must be a positive integer")

        self.base_url = normalize_base_url(resolved_base_url)
        self.api_key = resolved_api_key
        self.timeout = resolved_timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "sharebib-sdk/0.1.0",
            }
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        expect_json: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Make an HTTP request to the ShareBib API."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise ShareBibAPIError(f"Connection error: {exc}") from exc

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = f"HTTP {response.status_code}: {response.reason}"
            response_data: Any = None
            try:
                response_data = response.json()
                if isinstance(response_data, dict):
                    message = (
                        response_data.get("detail")
                        or response_data.get("message")
                        or message
                    )
            except ValueError:
                if response.text:
                    response_data = response.text
            raise ShareBibAPIError(
                message,
                status_code=response.status_code,
                response=response_data,
            ) from exc

        if not expect_json:
            return response.text

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ShareBibAPIError("Unexpected response format: expected JSON") from exc

    def get_current_user(self) -> CurrentUser:
        """Get information about the authenticated user."""
        response = self._request("GET", "/api/sdk/me")
        return CurrentUser.from_dict(response)

    def auth_info(self) -> CurrentUser:
        """Alias for get_current_user, convenient for CLI/auth workflows."""
        return self.get_current_user()

    def search_users(self, q: str, *, limit: int = 10) -> list[UserSummary]:
        """Search users by username for sharing workflows."""
        response = self._request(
            "GET",
            "/api/sdk/users/search",
            params={"q": q, "limit": limit},
        )
        return [UserSummary.from_dict(item) for item in response]

    def list_collections(self) -> list[Collection]:
        """List all collections accessible by the authenticated user."""
        response = self._request("GET", "/api/sdk/collections")
        return [Collection.from_dict(item) for item in response]

    def create_collection(
        self,
        title: str,
        description: str = "",
        visibility: str = "private",
        tags: Optional[list[str]] = None,
        collection_id: Optional[str] = None,
    ) -> Collection:
        """Create a new collection."""
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "visibility": visibility,
            "tags": tags or [],
        }
        if collection_id:
            payload["id"] = collection_id

        response = self._request("POST", "/api/sdk/collections", json=payload)
        return Collection.from_dict(response)

    def get_collection(self, collection_id: str) -> Collection:
        """Get a collection by ID."""
        response = self._request("GET", f"/api/sdk/collections/{collection_id}")
        return Collection.from_dict(response)

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection by ID."""
        self._request("DELETE", f"/api/sdk/collections/{collection_id}")

    def list_collection_permissions(
        self, collection_id: str
    ) -> list[CollectionPermissionEntry]:
        """List effective permissions for a collection."""
        response = self._request(
            "GET", f"/api/sdk/collections/{collection_id}/permissions"
        )
        return [CollectionPermissionEntry.from_dict(item) for item in response]

    def set_collection_permission(
        self,
        collection_id: str,
        *,
        user_id: str,
        permission: str,
    ) -> CollectionPermissionEntry:
        """Grant or replace a user's permission on a collection."""
        response = self._request(
            "POST",
            f"/api/sdk/collections/{collection_id}/permissions",
            json={"user_id": user_id, "permission": permission},
        )
        return CollectionPermissionEntry.from_dict(response)

    def remove_collection_permission(self, collection_id: str, user_id: str) -> None:
        """Remove a user's explicit permission from a collection."""
        self._request(
            "DELETE",
            f"/api/sdk/collections/{collection_id}/permissions/{user_id}",
        )

    def export_collection_bibtex(self, collection_id: str) -> str:
        """Export a collection as BibTeX text."""
        return self._request(
            "GET",
            f"/api/sdk/collections/{collection_id}/export/bibtex",
            expect_json=False,
        )

    def add_paper(
        self,
        collection_id: str,
        title: str,
        authors: Optional[list[str]] = None,
        venue: Optional[str] = None,
        year: Optional[int] = None,
        abstract: Optional[str] = None,
        summary: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
        url_arxiv: Optional[str] = None,
        url_pdf: Optional[str] = None,
        url_code: Optional[str] = None,
        url_project: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Paper:
        """Create a new paper and add it to a collection."""
        payload = {
            "title": title,
            "authors": authors or [],
            "venue": venue,
            "year": year,
            "abstract": abstract,
            "summary": summary,
            "arxiv_id": arxiv_id,
            "doi": doi,
            "url_arxiv": url_arxiv,
            "url_pdf": url_pdf,
            "url_code": url_code,
            "url_project": url_project,
            "tags": tags or [],
        }
        response = self._request(
            "POST",
            f"/api/sdk/collections/{collection_id}/papers",
            json=payload,
        )
        return Paper.from_dict(response)

    def list_papers(self, collection_id: str) -> list[Paper]:
        """List all papers in a collection."""
        response = self._request("GET", f"/api/sdk/collections/{collection_id}/papers")
        return [Paper.from_dict(item) for item in response]

    def search_papers(
        self,
        q: str,
        *,
        limit: int = 50,
        year: int | None = None,
        status: str | None = None,
    ) -> list[Paper]:
        """Search papers visible to the authenticated user."""
        params: dict[str, Any] = {"q": q, "limit": limit}
        if year is not None:
            params["year"] = year
        if status is not None:
            params["status"] = status
        response = self._request("GET", "/api/sdk/papers/search", params=params)
        return [Paper.from_dict(item) for item in response]

    def get_paper(self, paper_id: str) -> Paper:
        """Get a paper by ID."""
        response = self._request("GET", f"/api/sdk/papers/{paper_id}")
        return Paper.from_dict(response)

    def remove_paper(self, collection_id: str, paper_id: str) -> None:
        """Remove a paper from a collection."""
        self._request(
            "DELETE",
            f"/api/sdk/collections/{collection_id}/papers/{paper_id}",
        )
