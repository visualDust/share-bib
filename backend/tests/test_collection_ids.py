import pytest

from services.collection_ids import is_safe_collection_id, slugify_collection_name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("3/4DGS", "3-4dgs"),
        ("My Collection", "my-collection"),
        ("Résumé & Papers", "resume-papers"),
        ("研究论文", "collection"),
    ],
)
def test_slugify_collection_name(name: str, expected: str) -> None:
    assert slugify_collection_name(name) == expected


@pytest.mark.parametrize(
    "collection_id",
    ["col-1234abcd", "3-4dgs-20260723", "paper.list_2026"],
)
def test_safe_collection_ids(collection_id: str) -> None:
    assert is_safe_collection_id(collection_id)


@pytest.mark.parametrize(
    "collection_id",
    ["3/4dgs-20260723", "has spaces", "?query", "a" * 129],
)
def test_unsafe_collection_ids(collection_id: str) -> None:
    assert not is_safe_collection_id(collection_id)
