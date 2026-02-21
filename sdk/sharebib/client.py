"""
ShareBib API Client

Main client class for interacting with the ShareBib API.
"""

import requests
from typing import Optional
from .models import Collection, Paper


class ShareBibClient:
    """Client for ShareBib API"""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the ShareBib client.

        Args:
            base_url: Base URL of the ShareBib API (e.g., "http://localhost:11550")
            api_key: Your API key (starts with "pc_")
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    # Collection methods
    def list_collections(self) -> list[Collection]:
        """
        List all collections accessible by the user.

        Returns:
            List of Collection objects
        """
        response = self._request("GET", "/api/sdk/collections")
        return [Collection.from_dict(c) for c in response.json()]

    def create_collection(
        self,
        title: str,
        description: str = "",
        visibility: str = "private",
        tags: Optional[list[str]] = None,
        collection_id: Optional[str] = None,
    ) -> Collection:
        """
        Create a new collection.

        Args:
            title: Collection title
            description: Collection description (optional)
            visibility: Visibility setting ("private", "public", or "public_editable")
            tags: List of tags (optional)
            collection_id: Custom collection ID (optional, auto-generated if not provided)

        Returns:
            Created Collection object
        """
        data = {
            "title": title,
            "description": description,
            "visibility": visibility,
            "tags": tags or [],
        }
        if collection_id:
            data["id"] = collection_id

        response = self._request("POST", "/api/sdk/collections", json=data)
        return Collection.from_dict(response.json())

    def get_collection(self, collection_id: str) -> Collection:
        """
        Get a collection by ID.

        Args:
            collection_id: Collection ID

        Returns:
            Collection object
        """
        response = self._request("GET", f"/api/sdk/collections/{collection_id}")
        return Collection.from_dict(response.json())

    def delete_collection(self, collection_id: str) -> None:
        """
        Delete a collection.

        Args:
            collection_id: Collection ID
        """
        self._request("DELETE", f"/api/sdk/collections/{collection_id}")

    # Paper methods
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
        """
        Create a new paper and add it to a collection.

        Args:
            collection_id: Collection ID to add the paper to
            title: Paper title (required)
            authors: List of author names
            venue: Publication venue
            year: Publication year
            abstract: Paper abstract
            summary: Paper summary
            arxiv_id: arXiv ID
            doi: DOI
            url_arxiv: arXiv URL
            url_pdf: PDF URL
            url_code: Code repository URL
            url_project: Project page URL
            tags: List of tags

        Returns:
            Created Paper object
        """
        data = {
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
            "POST", f"/api/sdk/collections/{collection_id}/papers", json=data
        )
        return Paper.from_dict(response.json())

    def list_papers(self, collection_id: str) -> list[Paper]:
        """
        List all papers in a collection.

        Args:
            collection_id: Collection ID

        Returns:
            List of Paper objects
        """
        response = self._request("GET", f"/api/sdk/collections/{collection_id}/papers")
        return [Paper.from_dict(p) for p in response.json()]

    def get_paper(self, paper_id: str) -> Paper:
        """
        Get a paper by ID.

        Args:
            paper_id: Paper ID

        Returns:
            Paper object
        """
        response = self._request("GET", f"/api/sdk/papers/{paper_id}")
        return Paper.from_dict(response.json())

    def remove_paper(self, collection_id: str, paper_id: str) -> None:
        """
        Remove a paper from a collection.

        Args:
            collection_id: Collection ID
            paper_id: Paper ID
        """
        self._request(
            "DELETE", f"/api/sdk/collections/{collection_id}/papers/{paper_id}"
        )
