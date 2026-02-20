import re
import logging
from datetime import datetime

import feedparser

from crawl.types import FetchedPaper, SourceConfigField, SourceMeta
from crawl.sources.base import CrawlSource

logger = logging.getLogger(__name__)

# Complete list of CS arXiv categories
ARXIV_CS_CATEGORIES = [
    {"value": "cs.AI", "label": "Artificial Intelligence"},
    {"value": "cs.CL", "label": "Computation and Language"},
    {"value": "cs.CC", "label": "Computational Complexity"},
    {"value": "cs.CE", "label": "Computational Engineering"},
    {"value": "cs.CG", "label": "Computational Geometry"},
    {"value": "cs.GT", "label": "Computer Science and Game Theory"},
    {"value": "cs.CV", "label": "Computer Vision and Pattern Recognition"},
    {"value": "cs.CY", "label": "Computers and Society"},
    {"value": "cs.CR", "label": "Cryptography and Security"},
    {"value": "cs.DS", "label": "Data Structures and Algorithms"},
    {"value": "cs.DB", "label": "Databases"},
    {"value": "cs.DL", "label": "Digital Libraries"},
    {"value": "cs.DM", "label": "Discrete Mathematics"},
    {"value": "cs.DC", "label": "Distributed, Parallel, and Cluster Computing"},
    {"value": "cs.ET", "label": "Emerging Technologies"},
    {"value": "cs.FL", "label": "Formal Languages and Automata Theory"},
    {"value": "cs.GL", "label": "General Literature"},
    {"value": "cs.GR", "label": "Graphics"},
    {"value": "cs.AR", "label": "Hardware Architecture"},
    {"value": "cs.HC", "label": "Human-Computer Interaction"},
    {"value": "cs.IR", "label": "Information Retrieval"},
    {"value": "cs.IT", "label": "Information Theory"},
    {"value": "cs.LG", "label": "Machine Learning"},
    {"value": "cs.LO", "label": "Logic in Computer Science"},
    {"value": "cs.MA", "label": "Multiagent Systems"},
    {"value": "cs.MM", "label": "Multimedia"},
    {"value": "cs.MS", "label": "Mathematical Software"},
    {"value": "cs.NA", "label": "Numerical Analysis"},
    {"value": "cs.NE", "label": "Neural and Evolutionary Computing"},
    {"value": "cs.NI", "label": "Networking and Internet Architecture"},
    {"value": "cs.OH", "label": "Other Computer Science"},
    {"value": "cs.OS", "label": "Operating Systems"},
    {"value": "cs.PF", "label": "Performance"},
    {"value": "cs.PL", "label": "Programming Languages"},
    {"value": "cs.RO", "label": "Robotics"},
    {"value": "cs.SC", "label": "Symbolic Computation"},
    {"value": "cs.SD", "label": "Sound"},
    {"value": "cs.SE", "label": "Software Engineering"},
    {"value": "cs.SI", "label": "Social and Information Networks"},
    {"value": "cs.SY", "label": "Systems and Control"},
    # Other popular categories
    {"value": "stat.ML", "label": "Statistics - Machine Learning"},
    {"value": "eess.AS", "label": "Audio and Speech Processing"},
    {"value": "eess.IV", "label": "Image and Video Processing"},
    {"value": "eess.SP", "label": "Signal Processing"},
    {"value": "math.OC", "label": "Optimization and Control"},
]


class ArxivRSSSource(CrawlSource):
    @classmethod
    def meta(cls) -> SourceMeta:
        return SourceMeta(
            source_type="arxiv_rss",
            display_name="arXiv RSS",
            description="Subscribe to daily new papers by arXiv category",
            config_fields=[
                SourceConfigField(
                    key="categories",
                    label="Categories",
                    field_type="multiselect",
                    options=ARXIV_CS_CATEGORIES,
                ),
                SourceConfigField(
                    key="filter_keywords",
                    label="Filter Keywords",
                    field_type="keywords",
                    required=False,
                    description="Only include papers whose title/abstract contains these keywords (leave empty for all)",
                ),
            ],
            supported_schedules=["daily"],
            rate_limit=3.0,
        )

    async def fetch(
        self,
        config: dict,
        since: datetime | None,
        user_settings: dict | None = None,
    ) -> list[FetchedPaper]:
        config = self.validate_config(config)
        results = []
        seen_ids: set[str] = set()

        for cat in config["categories"]:
            try:
                feed = feedparser.parse(f"http://export.arxiv.org/rss/{cat}")
                for entry in feed.entries:
                    paper = self._parse_entry(entry)
                    if paper and paper.arxiv_id not in seen_ids:
                        if self._matches_keywords(paper, config.get("filter_keywords")):
                            results.append(paper)
                            if paper.arxiv_id:
                                seen_ids.add(paper.arxiv_id)
            except Exception as e:
                logger.error(f"Error fetching arXiv RSS for {cat}: {e}")

        return results

    def _parse_entry(self, entry) -> FetchedPaper | None:
        """Parse a single RSS feed entry into FetchedPaper."""
        title = getattr(entry, "title", "")
        if not title:
            return None

        # Clean title: remove category prefix like "(cs.AI)" and newlines
        title = re.sub(r"^\s*\([^)]+\)\s*", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            return None

        # Extract arXiv ID from link
        link = getattr(entry, "link", "")
        arxiv_id = self._extract_arxiv_id(link)
        if not arxiv_id:
            return None

        # Authors
        authors = []
        if hasattr(entry, "authors"):
            authors = [a.get("name", "") for a in entry.authors if a.get("name")]
        elif hasattr(entry, "author"):
            authors = [entry.author]

        # Abstract/summary
        abstract = getattr(entry, "summary", "")
        if abstract:
            # Clean HTML tags from RSS summary
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()
            abstract = re.sub(r"\s+", " ", abstract)

        # Categories/tags
        tags = []
        if hasattr(entry, "tags"):
            tags = [t.get("term", "") for t in entry.tags if t.get("term")]

        clean_id = re.sub(r"v\d+$", "", arxiv_id)

        return FetchedPaper(
            title=title,
            authors=authors if authors else None,
            abstract=abstract if abstract else None,
            arxiv_id=clean_id,
            url_arxiv=f"https://arxiv.org/abs/{clean_id}",
            url_pdf=f"https://arxiv.org/pdf/{clean_id}.pdf",
            tags=tags if tags else None,
        )

    def _extract_arxiv_id(self, url: str) -> str | None:
        """Extract arXiv ID from URL."""
        m = re.search(
            r"(?:arxiv\.org/(?:abs|pdf|html)/)?(\d{4}\.\d{4,5}(?:v\d+)?)", url
        )
        if m:
            return m.group(1)
        m = re.search(r"(?:arxiv\.org/(?:abs|pdf)/)?([a-z-]+/\d{7}(?:v\d+)?)", url)
        if m:
            return m.group(1)
        return None

    def _matches_keywords(
        self, paper: FetchedPaper, keywords: list[str] | None
    ) -> bool:
        """Check if paper matches the filter keywords.

        Syntax:
          keyword     — plain keyword (OR with other plain keywords)
          +keyword    — must be present (AND)
          -keyword    — must NOT be present (exclude)
          *           — wildcard, matches any characters

        All matching is case-insensitive on title + abstract.
        """
        if not keywords:
            return True
        text = f"{paper.title} {paper.abstract or ''}".lower()

        required = []  # +keyword: all must match
        excluded = []  # -keyword: none may match
        optional = []  # plain: at least one must match (if any)

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

        # All required keywords must match
        for kw in required:
            if not _match(kw, text):
                return False

        # No excluded keyword may match
        for kw in excluded:
            if _match(kw, text):
                return False

        # If there are optional keywords, at least one must match
        if optional and not any(_match(kw, text) for kw in optional):
            return False

        return True
