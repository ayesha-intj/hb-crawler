"""Parse one job page (https://startup.jobs/<slug>-<id>) into its details.
Strategy, most reliable first:
1. JSON-LD (<script type="application/ld+json">, @type JobPosting), the
   structured data job boards publish for search engines.
2. Meta tags (og:title, og:author, og:datePublished, og:description).
3. The visible page: <h1>, company / location / workplace links after it,
   and the section that follows the first <h2> for the description.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.crawler.listing_parser import workplace_from_link
from app.crawler.text import clean_html, parse_datetime, squash
from app.crawler.urls import absolute_url

EMPLOYMENT_TYPES = {"full-time", "part-time", "internship", "contractor"}
SCHEMA_EMPLOYMENT = {
    "FULL_TIME": "Full-Time",
    "PART_TIME": "Part-Time",
    "INTERN": "Internship",
    "CONTRACTOR": "Contractor",
}


@dataclass(slots=True)
class JobDetails:
    title: str
    company_name: str
    company_url: str | None
    location: str
    workplace: str | None
    employment_type: str | None
    salary_text: str | None
    posted_at: datetime | None
    description_html: str


def _walk(data: object) -> Iterator[dict]:
    """Yield every dict inside nested JSON lists and '@graph' containers."""
    if isinstance(data, list):
        for item in data:
            yield from _walk(item)
    elif isinstance(data, dict):
        yield data
        yield from _walk(data.get("@graph", []))


def find_job_posting(soup: BeautifulSoup) -> dict | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue  # one broken block must not break the page
        for item in _walk(data):
            kind = item.get("@type")
            if kind == "JobPosting" or (
                isinstance(kind, list) and "JobPosting" in kind
            ):
                return item
    return None


def _meta(soup: BeautifulSoup, key: str) -> str:
    tag = soup.find("meta", attrs={"property": key}) or soup.find(
        "meta", attrs={"name": key}
    )
    return squash(tag.get("content")) if tag else ""


def _name(value: object) -> str:
    if isinstance(value, dict):
        return squash(str(value.get("name") or ""))
    return squash(str(value or ""))


def _salary(posting: dict) -> str | None:
    base = posting.get("baseSalary")
    if not isinstance(base, dict):
        return None
    value = base.get("value") if isinstance(base.get("value"), dict) else {}
    low, high = value.get("minValue"), value.get("maxValue")
    if not (low or high):
        return None
    amount = f"{low:,.0f}–{high:,.0f}" if low and high else f"{(low or high):,.0f}"
    unit = str(value.get("unitText") or "").lower()
    return squash(
        f"{base.get('currency', '')} {amount} {('/ ' + unit) if unit else ''}"
    )


def _links_after_heading(h1: Tag | None, limit: int = 40) -> list[Tag]:
    return list(h1.find_all_next("a", href=True, limit=limit)) if h1 else []


def _description_from_page(h1: Tag | None) -> str:
    """The block that contains the first <h2> after the title holds the job text."""
    first_h2 = h1.find_next("h2") if h1 else None
    return clean_html(str(first_h2.parent)) if first_h2 and first_h2.parent else ""


def parse_job_page(html: str) -> JobDetails:
    soup = BeautifulSoup(html, "html.parser")
    posting = find_job_posting(soup) or {}
    h1 = soup.find("h1")
    links = _links_after_heading(h1)

    # Links right after the <h1>: locations, employment type and workplace badge.
    locations, workplace, employment = [], None, None
    for link in links:
        path = urlparse(absolute_url(link["href"])).path
        text = squash(link.get_text())
        if path.startswith("/locations/"):
            locations.append(text)
        elif workplace is None and workplace_from_link(link):
            workplace = workplace_from_link(link)
        elif employment is None and text.lower() in EMPLOYMENT_TYPES:
            employment = text
        if text.lower().startswith("apply"):
            break

    if posting.get("jobLocationType") == "TELECOMMUTE" and workplace is None:
        workplace = "remote"

    company_link = next(
        (
            a
            for a in soup.find_all("a", href=True)
            if urlparse(absolute_url(a["href"])).path.startswith("/company/")
            and squash(a.get_text())
        ),
        None,
    )
    company = _name(posting.get("hiringOrganization")) or _meta(soup, "og:author")
    if not company and company_link:
        company = squash(company_link.get_text())

    schema_type = posting.get("employmentType")
    if isinstance(schema_type, list):
        schema_type = schema_type[0] if schema_type else None

    return JobDetails(
        title=squash(posting.get("title"))
        or (squash(h1.get_text()) if h1 else "")
        or _meta(soup, "og:headline"),
        company_name=company,
        company_url=absolute_url(company_link["href"]) if company_link else None,
        location=", ".join(dict.fromkeys(filter(None, locations))),
        workplace=workplace,
        employment_type=employment or SCHEMA_EMPLOYMENT.get(str(schema_type), None),
        salary_text=_salary(posting),
        posted_at=parse_datetime(
            posting.get("datePosted") or _meta(soup, "og:datePublished")
        ),
        description_html=clean_html(posting.get("description"))
        or _description_from_page(h1)
        or clean_html(f"<p>{_meta(soup, 'og:description')}</p>"),
    )
