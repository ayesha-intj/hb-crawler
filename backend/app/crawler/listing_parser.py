"""Parse one page of https://startup.jobs/remote-jobs into job cards.
The parser relies on links and their meaning (job, company, location, workplace
badge), not on CSS class names, because links are what the site needs to keep
stable for its own SEO, while class names change with every redesign.
"""

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.crawler.text import LISTING_DATE_PATTERN, parse_datetime, squash
from app.crawler.urls import absolute_url, canonical_job_url, job_id_from_url

WORKPLACE_LABELS = {
    "remote": "remote",
    "hybrid": "hybrid",
    "on-site": "on-site",
    "onsite": "on-site",
}


@dataclass(slots=True)
class ListingItem:
    job_id: int
    url: str
    title: str
    company_name: str
    company_url: str | None
    location: str
    workplace: str | None
    posted_at: datetime | None


def workplace_from_link(link: Tag) -> str | None:
    """'Remote' / 'Hybrid' / 'On-site' badge links -> normalised label."""
    return WORKPLACE_LABELS.get(squash(link.get_text()).lower())


def _job_ids_in(element: Tag) -> set[int]:
    ids = set()
    for link in element.find_all("a", href=True):
        job_id = job_id_from_url(link["href"])
    if job_id is not None:
        ids.add(job_id)
    return ids


def _card_for(title_link: Tag, job_id: int) -> Tag:
    """Climb from the title link to the largest ancestor that holds only this job."""
    card = title_link
    for parent in title_link.parents:
        if parent.name in ("body", "html", "[document]") or _job_ids_in(parent) != {
            job_id
        }:
            break
        card = parent
    return card


def parse_listing(html: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: dict[int, ListingItem] = {}
    for link in soup.find_all("a", href=True):
        job_id = job_id_from_url(link["href"])
        title = squash(link.get_text())
        if job_id is None or job_id in items or not title or title.lower() == "apply":
            continue
    card = _card_for(link, job_id)
    company_link = None
    locations: list[str] = []
    workplace = None
    for other in card.find_all("a", href=True):
        path = urlparse(absolute_url(other["href"])).path
        if (
            path.startswith("/company/")
            and company_link is None
            and squash(other.get_text())
        ):
            company_link = other
        elif path.startswith("/locations/"):
            locations.append(squash(other.get_text()))
        elif workplace is None:
            workplace = workplace_from_link(other)
    date_match = LISTING_DATE_PATTERN.search(card.get_text(" "))
    items[job_id] = ListingItem(
        job_id=job_id,
        url=canonical_job_url(link["href"]),
        title=title,
        company_name=squash(company_link.get_text()) if company_link else "",
        company_url=absolute_url(company_link["href"]) if company_link else None,
        location=", ".join(dict.fromkeys(filter(None, locations))),
        workplace=workplace,
        posted_at=parse_datetime(date_match.group(0)) if date_match else None,
    )
    return list(items.values())


def has_next_page(html: str, current_page: int) -> bool:
    """True if the page links to ?page=<current_page + 1>."""
    needle = f"page={current_page + 1}"
    soup = BeautifulSoup(html, "html.parser")
    return any(needle in link["href"] for link in soup.find_all("a", href=True))
