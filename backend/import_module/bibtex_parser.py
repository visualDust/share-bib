import re
import logging

import bibtexparser
from bibtexparser.bparser import BibTexParser

logger = logging.getLogger(__name__)


def clean_latex(text: str) -> str:
    """Remove LaTeX formatting artifacts."""
    if not text:
        return text
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\\textit\s*", "", text)
    text = re.sub(r"\\textbf\s*", "", text)
    text = re.sub(r"\\emph\s*", "", text)
    text = text.replace("\\textbar", "|")
    text = text.replace("\\&", "&")
    text = text.replace("~", " ")
    return text.strip()


def parse_authors(author_string: str) -> list[str]:
    if not author_string:
        return []
    authors = []
    for author in author_string.split(" and "):
        author = clean_latex(author.strip())
        if not author:
            continue
        if "," in author:
            parts = author.split(",", 1)
            authors.append(f"{parts[1].strip()} {parts[0].strip()}")
        else:
            authors.append(author)
    return authors


def extract_arxiv_id(entry: dict) -> str | None:
    url = entry.get("url", "")
    if "arxiv.org/abs/" in url:
        return url.split("arxiv.org/abs/")[-1].split(".pdf")[0].split("v")[0].strip("/")
    eprint = entry.get("eprint", "")
    if eprint:
        return eprint.strip()
    note = entry.get("note", "")
    match = re.search(r"arXiv[:\s]*(\d+\.\d+)", note)
    if match:
        return match.group(1)
    return None


def extract_summary(entry: dict) -> str | None:
    abstract = entry.get("abstract", "").strip()
    if abstract:
        return clean_latex(abstract)
    note = entry.get("note", "")
    if "TLDR:" in note:
        return note.split("TLDR:", 1)[1].strip()
    if "tldr:" in note.lower():
        idx = note.lower().index("tldr:")
        return note[idx + 5 :].strip()
    return None


def extract_tags(entry: dict) -> list[str]:
    tags = []
    keywords = entry.get("keywords", "")
    if keywords:
        tags.extend([k.strip() for k in keywords.split(",") if k.strip()])
    return tags


def extract_year(entry: dict) -> int | None:
    year = entry.get("year", "")
    if year:
        try:
            return int(re.sub(r"[^0-9]", "", year))
        except ValueError:
            pass
    return None


def parse_bibtex_content(content: str) -> list[dict]:
    """Parse BibTeX content and return list of paper dicts."""
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    try:
        bib_db = bibtexparser.loads(content, parser)
    except Exception as e:
        logger.error(f"BibTeX parse error: {e}")
        return []

    papers = []
    errors = []

    for entry in bib_db.entries:
        entry_id = entry.get("ID", "unknown")
        title = clean_latex(entry.get("title", ""))
        if not title:
            errors.append({"entry_id": entry_id, "reason": "Missing title"})
            continue

        arxiv_id = extract_arxiv_id(entry)
        url = entry.get("url", "").strip()
        doi = entry.get("doi", "").strip() or None

        url_arxiv = None
        url_pdf = None
        if arxiv_id:
            url_arxiv = f"https://arxiv.org/abs/{arxiv_id}"
            url_pdf = f"https://arxiv.org/pdf/{arxiv_id}"
        elif url:
            if "arxiv.org" in url:
                url_arxiv = url
            else:
                url_pdf = url

        venue = clean_latex(
            entry.get("booktitle", "") or entry.get("journal", "") or "Unknown"
        )
        status = "accessible" if (url_arxiv or url_pdf) else "no_access"

        papers.append(
            {
                "title": title,
                "authors": parse_authors(entry.get("author", "")),
                "venue": venue,
                "year": extract_year(entry),
                "abstract": clean_latex(entry.get("abstract", "")) or None,
                "summary": extract_summary(entry),
                "status": status,
                "bibtex_key": entry_id,  # Store the BibTeX key
                "arxiv_id": arxiv_id,
                "doi": doi,
                "url_arxiv": url_arxiv,
                "url_pdf": url_pdf,
                "url_code": None,
                "url_project": None,
                "tags": extract_tags(entry),
                "_entry_id": entry_id,
            }
        )

    return papers
