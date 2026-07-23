import re
import unicodedata


_SAFE_COLLECTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def is_safe_collection_id(value: str) -> bool:
    """Return whether an ID can be used as one URL path segment."""

    return bool(_SAFE_COLLECTION_ID.fullmatch(value))


def slugify_collection_name(value: str, max_length: int = 50) -> str:
    """Build a stable, URL-path-safe slug from a collection display name."""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or "collection"
