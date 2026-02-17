import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def sanitize_bibtex_key(title: str, authors: List[str], year: int | None) -> str:
    """Generate a BibTeX citation key from paper metadata."""
    # Get first author's last name
    first_author = "unknown"
    if authors and len(authors) > 0:
        # Extract last name (assume format is "First Last" or just "Last")
        parts = authors[0].strip().split()
        first_author = parts[-1] if parts else "unknown"

    # Clean the author name for use in key
    first_author = re.sub(r"[^a-zA-Z0-9]", "", first_author).lower()

    # Get year or use "nodate"
    year_str = str(year) if year else "nodate"

    # Get first significant word from title
    title_words = re.findall(r"\b[a-zA-Z]{3,}\b", title.lower())
    title_word = title_words[0] if title_words else "paper"

    return f"{first_author}{year_str}{title_word}"


def escape_bibtex_string(text: str) -> str:
    """Escape special characters for BibTeX."""
    if not text:
        return ""
    # Escape special LaTeX characters
    text = text.replace("\\", "\\textbackslash ")
    text = text.replace("&", "\\&")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("_", "\\_")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("~", "\\textasciitilde ")
    text = text.replace("^", "\\textasciicircum ")
    return text


def format_authors_bibtex(authors: List[str]) -> str:
    """Format authors list for BibTeX."""
    if not authors:
        return ""
    return " and ".join(authors)


def paper_to_bibtex_entry(paper: Dict[str, Any]) -> str:
    """Convert a paper dict to a BibTeX entry string."""
    # Generate citation key
    cite_key = sanitize_bibtex_key(
        paper.get("title", ""), paper.get("authors", []), paper.get("year")
    )

    # Determine entry type
    venue = paper.get("venue", "").lower()
    if any(conf in venue for conf in ["conference", "proceedings", "workshop"]):
        entry_type = "inproceedings"
    elif any(jour in venue for jour in ["journal", "transactions"]):
        entry_type = "article"
    else:
        entry_type = "misc"

    # Start building the entry
    lines = [f"@{entry_type}{{{cite_key},"]

    # Add title (required)
    title = escape_bibtex_string(paper.get("title", ""))
    lines.append(f"  title = {{{title}}},")

    # Add authors
    authors = paper.get("authors", [])
    if authors:
        author_str = format_authors_bibtex(authors)
        lines.append(f"  author = {{{author_str}}},")

    # Add year
    year = paper.get("year")
    if year:
        lines.append(f"  year = {{{year}}},")

    # Add venue (booktitle for inproceedings, journal for article)
    venue = paper.get("venue")
    if venue and venue != "Unknown":
        venue_escaped = escape_bibtex_string(venue)
        if entry_type == "inproceedings":
            lines.append(f"  booktitle = {{{venue_escaped}}},")
        elif entry_type == "article":
            lines.append(f"  journal = {{{venue_escaped}}},")
        else:
            lines.append(f"  howpublished = {{{venue_escaped}}},")

    # Add abstract
    abstract = paper.get("abstract")
    if abstract:
        abstract_escaped = escape_bibtex_string(abstract)
        lines.append(f"  abstract = {{{abstract_escaped}}},")

    # Add DOI
    doi = paper.get("doi")
    if doi:
        lines.append(f"  doi = {{{doi}}},")

    # Add arXiv ID
    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        lines.append(f"  eprint = {{{arxiv_id}}},")
        lines.append("  archivePrefix = {arXiv},")

    # Add URLs
    url_arxiv = paper.get("url_arxiv")
    url_pdf = paper.get("url_pdf")
    url_code = paper.get("url_code")
    url_project = paper.get("url_project")

    # Prefer arXiv URL, then PDF, then others
    if url_arxiv:
        lines.append(f"  url = {{{url_arxiv}}},")
    elif url_pdf:
        lines.append(f"  url = {{{url_pdf}}},")
    elif url_project:
        lines.append(f"  url = {{{url_project}}},")

    # Add code URL as note if available
    if url_code:
        lines.append(f"  note = {{Code: {url_code}}},")

    # Add keywords/tags
    tags = paper.get("tags", [])
    if tags:
        keywords = ", ".join(tags)
        lines.append(f"  keywords = {{{keywords}}},")

    # Close the entry (remove trailing comma from last line)
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("}")

    return "\n".join(lines)


def export_papers_to_bibtex(papers: List[Dict[str, Any]]) -> str:
    """Export a list of papers to BibTeX format."""
    if not papers:
        return ""

    entries = []
    for paper in papers:
        try:
            entry = paper_to_bibtex_entry(paper)
            entries.append(entry)
        except Exception as e:
            logger.error(
                f"Error exporting paper '{paper.get('title', 'unknown')}': {e}"
            )
            continue

    return "\n\n".join(entries)
