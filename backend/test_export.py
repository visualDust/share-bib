#!/usr/bin/env python3
"""Test script for BibTeX export functionality."""

from import_module.bibtex_exporter import export_papers_to_bibtex

# Test data
test_papers = [
    {
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        "venue": "NeurIPS",
        "year": 2017,
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        "summary": None,
        "status": "accessible",
        "arxiv_id": "1706.03762",
        "doi": None,
        "url_arxiv": "https://arxiv.org/abs/1706.03762",
        "url_pdf": "https://arxiv.org/pdf/1706.03762",
        "url_code": "https://github.com/tensorflow/tensor2tensor",
        "url_project": None,
        "tags": ["transformer", "attention", "nlp"],
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": [
            "Jacob Devlin",
            "Ming-Wei Chang",
            "Kenton Lee",
            "Kristina Toutanova",
        ],
        "venue": "NAACL",
        "year": 2019,
        "abstract": "We introduce a new language representation model called BERT.",
        "summary": None,
        "status": "accessible",
        "arxiv_id": "1810.04805",
        "doi": "10.18653/v1/N19-1423",
        "url_arxiv": "https://arxiv.org/abs/1810.04805",
        "url_pdf": None,
        "url_code": None,
        "url_project": None,
        "tags": ["bert", "pretraining", "nlp"],
    },
]

if __name__ == "__main__":
    print("Testing BibTeX export...")
    print("=" * 80)

    bibtex_output = export_papers_to_bibtex(test_papers)

    print(bibtex_output)
    print("=" * 80)
    print(f"\nExported {len(test_papers)} papers successfully!")

    # Save to file for inspection
    with open("/tmp/test_export.bib", "w", encoding="utf-8") as f:
        f.write(bibtex_output)
    print("Output saved to /tmp/test_export.bib")
