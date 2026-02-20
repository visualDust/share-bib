import logging
import asyncio
from datetime import datetime

import httpx

from crawl.types import FetchedPaper, SourceConfigField, SourceMeta
from crawl.sources.base import CrawlSource

logger = logging.getLogger(__name__)

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,abstract,authors,year,venue,externalIds,openAccessPdf,citationCount,publicationDate"

FIELDS_OF_STUDY = [
    {"value": "Computer Science", "label": "Computer Science"},
    {"value": "Mathematics", "label": "Mathematics"},
    {"value": "Physics", "label": "Physics"},
    {"value": "Biology", "label": "Biology"},
    {"value": "Medicine", "label": "Medicine"},
    {"value": "Chemistry", "label": "Chemistry"},
    {"value": "Engineering", "label": "Engineering"},
    {"value": "Materials Science", "label": "Materials Science"},
    {"value": "Environmental Science", "label": "Environmental Science"},
    {"value": "Economics", "label": "Economics"},
    {"value": "Business", "label": "Business"},
    {"value": "Political Science", "label": "Political Science"},
    {"value": "Psychology", "label": "Psychology"},
    {"value": "Sociology", "label": "Sociology"},
    {"value": "Linguistics", "label": "Linguistics"},
    {"value": "Philosophy", "label": "Philosophy"},
    {"value": "Geography", "label": "Geography"},
    {"value": "History", "label": "History"},
    {"value": "Art", "label": "Art"},
    {"value": "Education", "label": "Education"},
]


class SemanticScholarSource(CrawlSource):
    @classmethod
    def meta(cls) -> SourceMeta:
        return SourceMeta(
            source_type="semantic_scholar",
            display_name="Semantic Scholar",
            description="Search papers via Semantic Scholar API (200M+ papers)",
            config_fields=[
                SourceConfigField(
                    key="query",
                    label="Search Query",
                    field_type="text",
                    required=True,
                    description="Keywords to search for in paper titles and abstracts",
                ),
                SourceConfigField(
                    key="fields_of_study",
                    label="Fields of Study",
                    field_type="multiselect",
                    required=False,
                    options=FIELDS_OF_STUDY,
                    description="Filter by academic discipline (leave empty for all)",
                ),
                SourceConfigField(
                    key="year",
                    label="Year Range",
                    field_type="text",
                    required=False,
                    description='e.g. "2024" or "2023-2025" or "2024-"',
                ),
                SourceConfigField(
                    key="min_citation_count",
                    label="Min Citations",
                    field_type="number",
                    required=False,
                    default=0,
                    min_value=0,
                    max_value=100000,
                    description="Minimum citation count (0 = no filter)",
                ),
                SourceConfigField(
                    key="limit",
                    label="Max Papers",
                    field_type="number",
                    required=False,
                    default=100,
                    min_value=1,
                    max_value=1000,
                    description="Maximum number of papers to fetch per run",
                ),
                SourceConfigField(
                    key="filter_keywords",
                    label="Local Filter Keywords",
                    field_type="keywords",
                    required=False,
                    description="Additional local filtering on results (same syntax as arXiv RSS)",
                ),
            ],
            supported_schedules=["daily", "weekly", "monthly"],
            rate_limit=1.0,
        )

    async def fetch(
        self,
        config: dict,
        since: datetime | None,
        user_settings: dict | None = None,
    ) -> list[FetchedPaper]:
        config = self.validate_config(config)
        query = config["query"]
        if not query:
            return []

        limit = config.get("limit") or 100
        limit = min(limit, 1000)

        # Build query params
        params: dict = {
            "query": query,
            "fields": S2_FIELDS,
        }

        fos = config.get("fields_of_study")
        if fos:
            params["fieldsOfStudy"] = ",".join(fos)

        year = config.get("year")
        if year:
            params["year"] = year

        min_cite = config.get("min_citation_count")
        if min_cite and min_cite > 0:
            params["minCitationCount"] = str(min_cite)

        # API key from user settings
        headers = {}
        api_key = (user_settings or {}).get("semantic_scholar_api_key")
        if api_key:
            headers["x-api-key"] = api_key

        results: list[FetchedPaper] = []
        token = None
        retries_left = 3  # Max 3 retries for 429

        async with httpx.AsyncClient(timeout=30) as client:
            while len(results) < limit:
                req_params = {**params}
                if token:
                    req_params["token"] = token

                try:
                    resp = await client.get(
                        f"{S2_BASE}/paper/search/bulk",
                        params=req_params,
                        headers=headers,
                    )
                    if resp.status_code == 429:
                        retries_left -= 1
                        if retries_left <= 0:
                            logger.error(
                                "Semantic Scholar rate limit exceeded after retries"
                            )
                            raise RuntimeError(
                                "Semantic Scholar API rate limit exceeded"
                            )
                        logger.warning(
                            f"Semantic Scholar rate limited, waiting 5s ({retries_left} retries left)"
                        )
                        await asyncio.sleep(5)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    retries_left = 3  # Reset retry count on success
                except httpx.HTTPStatusError as e:
                    logger.error(f"Semantic Scholar API error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Semantic Scholar request failed: {e}")
                    raise

                papers = data.get("data") or []
                if not papers:
                    break

                for p in papers:
                    if len(results) >= limit:
                        break
                    fetched = self._parse_paper(p)
                    if fetched and self._matches_keywords(
                        fetched, config.get("filter_keywords")
                    ):
                        results.append(fetched)

                token = data.get("token")
                if not token:
                    break

                # Rate limiting: respect 1 RPS
                await asyncio.sleep(1.0)

        return results

    def _parse_paper(self, data: dict) -> FetchedPaper | None:
        title = data.get("title")
        if not title:
            return None

        # External IDs
        ext_ids = data.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv")
        doi = ext_ids.get("DOI")

        # Authors
        authors = None
        raw_authors = data.get("authors")
        if raw_authors:
            authors = [a.get("name") for a in raw_authors if a.get("name")]

        # PDF URL
        url_pdf = None
        oap = data.get("openAccessPdf")
        if oap and oap.get("url"):
            url_pdf = oap["url"]

        # arXiv URLs
        url_arxiv = None
        if arxiv_id:
            url_arxiv = f"https://arxiv.org/abs/{arxiv_id}"
            if not url_pdf:
                url_pdf = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        return FetchedPaper(
            title=title,
            authors=authors,
            abstract=data.get("abstract"),
            year=data.get("year"),
            venue=data.get("venue") or None,
            arxiv_id=arxiv_id,
            doi=doi,
            url_arxiv=url_arxiv,
            url_pdf=url_pdf,
        )

    def _matches_keywords(
        self, paper: FetchedPaper, keywords: list[str] | None
    ) -> bool:
        """Reuse the same keyword filtering logic as arXiv RSS source."""
        import re

        if not keywords:
            return True
        text = f"{paper.title} {paper.abstract or ''}".lower()

        required = []
        excluded = []
        optional = []

        for raw in keywords:
            kw = raw.strip()
            if not kw:
                continue
            if kw.startswith("+"):
                required.append(kw[1:].lower())
            elif kw.startswith("-"):
                excluded.append(kw[1:].lower())
            else:
                optional.append(kw.lower())

        def _match(pattern: str, text: str) -> bool:
            if "*" in pattern:
                regex = re.escape(pattern).replace(r"\*", ".*")
                return bool(re.search(regex, text))
            return pattern in text

        for kw in required:
            if not _match(kw, text):
                return False
        for kw in excluded:
            if _match(kw, text):
                return False
        if optional and not any(_match(kw, text) for kw in optional):
            return False

        return True
