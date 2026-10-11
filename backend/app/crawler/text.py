"""Small helpers for cleaning HTML and reading dates."""

import re
from datetime import UTC, datetime
import nh3

ALLOWED_TAGS = {
    "a",
    "b",
    "br",
    "em",
    "h2",
    "h3",
    "h4",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "ul",
}
LISTING_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC")


def clean_html(html: str | None) -> str:
    """Keep simple formatting only: removes scripts, styles, event handlers, iframes."""
    if not html:
        return ""
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes={"a": {"href"}}).strip()


def squash(text: str | None) -> str:
    """Collapse runs of whitespace into single spaces."""
    return " ".join((text or "").split())


def parse_datetime(value: str | None) -> datetime | None:
    """Read '2026-10-08 09:07:53 UTC' (listing) or ISO 8601 (meta tags, JSON-LD)."""
    if not value:
        return None
    value = value.strip().replace(" UTC", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
