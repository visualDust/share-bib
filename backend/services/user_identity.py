import re

from email_validator import EmailNotValidError, validate_email


_USERNAME_PARTS = re.compile(r"[^A-Za-z0-9_.-]+")


def normalize_oauth_username(value: object, oauth_sub: str) -> str:
    """Convert provider-controlled profile text into a route-safe username."""
    candidate = str(value or "").strip()
    if "@" in candidate:
        candidate = candidate.split("@", 1)[0]
    candidate = _USERNAME_PARTS.sub("-", candidate).strip("._-")
    if not candidate or not candidate[0].isalnum():
        candidate = f"user-{oauth_sub[:12]}"
    candidate = candidate[:64].rstrip("._-")
    if len(candidate) < 3:
        candidate = f"user-{oauth_sub[:12]}"
    return candidate[:64]


def suffix_oauth_username(base_username: str, counter: int) -> str:
    """Add a collision suffix without exceeding the 64-character limit."""
    suffix = f"_{counter}"
    prefix = base_username[: 64 - len(suffix)].rstrip("._-")
    return f"{prefix}{suffix}"


def normalize_oauth_email(value: object) -> str | None:
    if not value:
        return None
    try:
        return validate_email(str(value), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


def normalize_display_name(value: object, fallback: str) -> str:
    display_name = str(value or "").strip()
    return (display_name or fallback)[:200]
