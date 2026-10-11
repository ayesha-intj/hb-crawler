"""Everything the crawler knows about startup.jobs URLs."""

import re
from urllib.parse import urljoin, urlparse

BASE_URL = "https://startup.jobs"
ROBOTS_URL = f"{BASE_URL}/robots.txt"

# Server-rendered list of remote jobs, newest first (same filter as /?w=remote,
# which only renders its results with JavaScript).
REMOTE_LISTING_URL = f"{BASE_URL}/remote-jobs"

# A job page has exactly one path segment ending in "-<digits>":
# /senior-full-stack-engineer-solace-6654883 -> job id 6654883
JOB_PATH_PATTERN = re.compile(r"^/[a-z0-9-]+-(\d+)/?$")

# Belt and braces: paths we never request, even if robots.txt changed.
FORBIDDEN_PATH_PATTERN = re.compile(
    r"(/apply(/|$)|^/(login|signup|passwords|plus|account|employers|cdn-cgi)(/|$))"
)


def absolute_url(href: str) -> str:
    return urljoin(BASE_URL, href)


def listing_page_url(page: int) -> str:
    return REMOTE_LISTING_URL if page == 1 else f"{REMOTE_LISTING_URL}?page={page}"


def job_id_from_url(url: str) -> int | None:
    """Return the numeric job id if `url` is a startup.jobs job page, else None."""
    parsed = urlparse(absolute_url(url))
    if parsed.netloc not in ("startup.jobs", "www.startup.jobs") or parsed.query:
        return None
    match = JOB_PATH_PATTERN.match(parsed.path)
    return int(match.group(1)) if match else None


def canonical_job_url(url: str) -> str:
    """Strip query strings, fragments and trailing slashes."""
    parsed = urlparse(absolute_url(url))
    return f"{BASE_URL}{parsed.path.rstrip('/')}"


def is_forbidden(url: str) -> bool:
    return bool(FORBIDDEN_PATH_PATTERN.search(urlparse(url).path))
