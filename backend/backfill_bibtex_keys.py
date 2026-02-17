#!/usr/bin/env python3
"""
Backfill bibtex_key for existing papers that don't have one.
Generates a simple key from title: first word + year.
"""

import re
from database import SessionLocal
from models import Paper


def generate_bibtex_key(title: str, year: int | None) -> str:
    """Generate a simple BibTeX key from title and year."""
    # Get first meaningful word from title
    words = re.findall(r"\w+", title.lower())
    first_word = words[0] if words else "paper"
    year_str = str(year) if year else "unknown"
    return f"{first_word}{year_str}"


def main():
    db = SessionLocal()
    try:
        # Find papers without bibtex_key
        papers = db.query(Paper).filter(Paper.bibtex_key.is_(None)).all()
        print(f"Found {len(papers)} papers without bibtex_key")

        updated = 0
        for paper in papers:
            # Generate a key
            key = generate_bibtex_key(paper.title, paper.year)

            # Check if key already exists, if so add a suffix
            existing = db.query(Paper).filter(Paper.bibtex_key == key).first()
            if existing:
                suffix = 1
                while (
                    db.query(Paper)
                    .filter(Paper.bibtex_key == f"{key}_{suffix}")
                    .first()
                ):
                    suffix += 1
                key = f"{key}_{suffix}"

            paper.bibtex_key = key
            updated += 1

            if updated % 10 == 0:
                print(f"Updated {updated} papers...")

        db.commit()
        print(f"Successfully updated {updated} papers")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
