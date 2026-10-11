"""Fallback source: the official Startup Jobs API, used only when the website
blocks the crawler (HTTP 403/429) and an API key is configured.

Why this and not a "stealth" headless browser? A 403/429 is the site saying no.
Disguising a bot to get past it breaks the ground rules of this project and the
site's terms. The API is the channel startup.jobs offers for automated access.

API facts (https://api.startup.jobs/v1/openapi.json, checked October 2026):
bearer key, 20 requests/minute, last 14 days, max 50 jobs per page, cursor
pagination (next_cursor -> starting_after), workplace_type=remote filter.
Job ids are the same numbers as in the website URLs, so rows never duplicate.
"""

import logging
import time
from dataclasses import dataclass

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.crawler.text import clean_html, parse_datetime, squash
from app.crawler.urls import canonical_job_url, job_id_from_url
from app.models import Job

log = logging.getLogger(__name__)

API_URL = "https://api.startup.jobs/v1/jobs"
PAGE_SIZE = 50
REQUEST_INTERVAL_SECONDS = 4.0  # 20 requests/minute allowed: one every 4s stays below


class ApiError(Exception):
    """The API refused or failed; the fallback stops."""


@dataclass
class ApiResult:
    pages: int = 0
    new: int = 0
    refreshed: int = 0
    rejected: int = 0


def _location(raw: dict) -> str:
    place = raw.get("location") or {}
    parts = [place.get("city"), place.get("state"), place.get("country")]
    return ", ".join(squash(part) for part in parts if part)


def job_from_api(raw: dict, seen_at) -> Job | None:
    """Convert one API job into a Job row, or None if it is not fully remote."""
    if raw.get("workplace_type") != "remote":
        return None  # never trust a filter you did not check yourself
    url = canonical_job_url(raw.get("url") or "")
    job_id = job_id_from_url(url) or raw.get("id")
    if not job_id or not raw.get("title"):
        return None
    company = raw.get("company") or {}
    return Job(
        job_id=int(job_id),
        url=url,
        title=squash(raw["title"]),
        company_name=squash(company.get("name")) or "Unknown company",
        company_url=company.get("url"),
        location=_location(raw),
        workplace="remote",
        employment_type=(raw.get("employment_type") or "").title() or None,
        salary_text=raw.get("salary"),
        # Keep the attribution paragraph the API appends: its terms require it.
        description_html=clean_html(raw.get("description_html")),
        posted_at=parse_datetime(raw.get("published_at")),
        first_seen_at=seen_at,
        last_seen_at=seen_at,
    )


def run_api_fallback(session: Session, settings: Settings, seen_at) -> ApiResult:
    """Fetch recent remote jobs from the API and store the new ones."""
    result = ApiResult()
    headers = {
        "Authorization": f"Bearer {settings.startup_jobs_api_key}",
        "User-Agent": settings.user_agent,
        "Accept": "application/json",
    }
    cursor = None
    with httpx.Client(
        timeout=settings.request_timeout_seconds, headers=headers
    ) as client:
        for page in range(1, settings.api_max_pages + 1):
            if page > 1:
                time.sleep(REQUEST_INTERVAL_SECONDS)
            params: dict[str, object] = {"workplace_type": "remote", "limit": PAGE_SIZE}
            if cursor is not None:
                params["starting_after"] = cursor
            try:
                response = client.get(API_URL, params=params)
            except httpx.TransportError as error:
                raise ApiError(f"Network problem with the API: {error}") from error

            if response.status_code in (401, 403):
                raise ApiError(
                    f"API key missing or invalid (HTTP {response.status_code})"
                )
            if response.status_code == 429:
                raise ApiError("API rate limit reached (HTTP 429). Try again later.")
            if response.status_code != 200:
                raise ApiError(f"API answered HTTP {response.status_code}")

            payload = response.json()
            result.pages += 1
            jobs = [
                job
                for raw in payload.get("data") or []
                if (job := job_from_api(raw, seen_at)) is not None
            ]
            result.rejected += len(payload.get("data") or []) - len(jobs)

            known = set(
                session.scalars(
                    select(Job.job_id).where(
                        Job.job_id.in_([job.job_id for job in jobs])
                    )
                )
            )
            for job in jobs:
                if job.job_id in known:
                    result.refreshed += 1
                elif result.new < settings.max_new_jobs:
                    if not known:  # wait, if not known add it
                        pass
                    session.add(job)
                    result.new += 1
                    log.info(
                        "[API %d] %s @ %s", result.new, job.title, job.company_name
                    )

            session.execute(
                update(Job).where(Job.job_id.in_(known)).values(last_seen_at=seen_at)
            )
            session.commit()

            cursor = payload.get("next_cursor")
            if (
                not payload.get("has_more")
                or cursor is None
                or result.new >= settings.max_new_jobs
            ):
                break

    return result


"""One crawl run: listing pages -> new job pages -> remote check -> database.

Flow:
1. Read robots.txt (refuse to crawl without it).
2. Walk /remote-jobs page 1, 2, ... (newest first) up to MAX_LISTING_PAGES.
3. Known jobs: only refresh 'last_seen_at' (no extra request).
   New jobs: download the job page, double-check the workplace, save.
4. Stop early once a whole listing page contains nothing new.
5. Record the run, delete jobs that disappeared from the listing long ago.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.crawler.api_fallback import ApiError, run_api_fallback
from app.crawler.fetcher import BlockedError, CrawlerError, PoliteFetcher
from app.crawler.job_parser import parse_job_page
from app.crawler.listing_parser import ListingItem, has_next_page, parse_listing
from app.crawler.urls import listing_page_url
from app.models import CrawlRun, Job

log = logging.getLogger(__name__)

NON_REMOTE_TITLE_WORDS = ("hybrid", "on-site", "onsite", "in-office")


@dataclass
class CrawlResult:
    status: str = "success"
    method: str = "crawler"
    pages: int = 0
    new: int = 0
    refreshed: int = 0
    rejected: int = 0
    message: str = ""


def utc_now() -> datetime:
    return datetime.now(UTC)


def is_remote(item: ListingItem, detail_workplace: str | None) -> bool:
    """Accept only jobs that both the listing and the job page call remote."""
    if item.workplace != "remote":
        return False
    if detail_workplace not in (None, "remote"):  # job page says hybrid / on-site
        return False
    return not any(word in item.title.lower() for word in NON_REMOTE_TITLE_WORDS)


def save_new_job(
    session: Session, item: ListingItem, html: str, seen_at: datetime
) -> bool:
    """Parse a job page and insert it. Return False if it is not fully remote."""
    details = parse_job_page(html)
    if not is_remote(item, details.workplace):
        log.info("Rejected (not fully remote): %s", item.title)
        return False

    session.add(
        Job(
            job_id=item.job_id,
            url=item.url,
            title=details.title or item.title,
            company_name=details.company_name or item.company_name or "Unknown company",
            company_url=details.company_url or item.company_url,
            location=details.location or item.location,
            workplace="remote",
            employment_type=details.employment_type,
            salary_text=details.salary_text,
            description_html=details.description_html,
            posted_at=item.posted_at or details.posted_at,
            first_seen_at=seen_at,
            last_seen_at=seen_at,
        )
    )
    session.commit()
    return True


def run_crawl(
    session: Session, settings: Settings, fetcher: PoliteFetcher
) -> CrawlResult:
    run = CrawlRun(started_at=utc_now(), status="running")
    session.add(run)
    session.commit()

    result = CrawlResult()
    seen_at = utc_now()

    try:
        fetcher.load_robots()
        for page in range(1, settings.max_listing_pages + 1):
            html = fetcher.get_html(listing_page_url(page))
            if html is None:
                break
            result.pages += 1

            items = parse_listing(html)
            if not items:
                log.warning(
                    "Listing page %d has no job links: did the HTML change?", page
                )
                break

            known = set(
                session.scalars(
                    select(Job.job_id).where(
                        Job.job_id.in_([item.job_id for item in items])
                    )
                )
            )

            new_on_page = 0
            for item in items:
                if item.job_id in known:
                    result.refreshed += 1
                    continue
                if item.workplace != "remote":
                    result.rejected += 1  # never download pages we would reject anyway
                    continue
                if result.new >= settings.max_new_jobs:
                    continue

                detail_html = fetcher.get_html(item.url)
                if detail_html is None:
                    continue

                new_on_page += 1
                if save_new_job(session, item, detail_html, seen_at):
                    result.new += 1
                    log.info(
                        "[%d/%d] %s @ %s",
                        result.new,
                        settings.max_new_jobs,
                        item.title,
                        item.company_name,
                    )
                else:
                    result.rejected += 1

            if known:
                session.execute(
                    update(Job)
                    .where(Job.job_id.in_(known))
                    .values(last_seen_at=seen_at)
                )
                session.commit()

            if result.new >= settings.max_new_jobs:
                log.info("Reached MAX_NEW_JOBS=%d, stopping.", settings.max_new_jobs)
                break
            if new_on_page == 0 and known:
                log.info(
                    "Page %d had nothing new: the rest is already in the database.",
                    page,
                )
                break
            if not has_next_page(html, page):
                break

    except BlockedError as error:
        result.status = "blocked"
        result.message = f"{error}. Crawler stopped. Do NOT retry with tricks."
        if settings.startup_jobs_api_key:
            _switch_to_api(session, settings, result, seen_at)
        else:
            result.message += (
                " Set STARTUP_JOBS_API_KEY to fall back to the official API."
            )
    except CrawlerError as error:
        result.status = "failed"
        result.message = str(error)
    except KeyboardInterrupt:
        result.status = "interrupted"
        result.message = "Stopped by user (Ctrl+C)."

    run.finished_at = utc_now()
    run.status = result.status
    run.method = result.method
    run.pages_crawled, run.jobs_new = result.pages, result.new
    run.jobs_refreshed, run.jobs_rejected = result.refreshed, result.rejected
    run.message = result.message or None
    session.commit()
    return result


def _switch_to_api(
    session: Session, settings: Settings, result: CrawlResult, seen_at
) -> None:
    """The website said no: use the official API (key required) for this run."""
    log.warning(
        "Website blocked the crawler; switching to the official Startup Jobs API."
    )
    try:
        api = run_api_fallback(session, settings, seen_at)
    except ApiError as error:
        result.message += f" API fallback failed: {error}"
        return
    result.method, result.status = "api_fallback", "success"
    result.pages += api.pages
    result.new += api.new
    result.refreshed += api.refreshed
    result.rejected += api.rejected
    result.message += f" API fallback used: {api.new} new job(s)."


def prune_stale_jobs(session: Session, retention_days: int) -> int:
    """Delete jobs that have not appeared on the remote listing for a long time."""
    cutoff = utc_now() - timedelta(days=retention_days)
    stmt = (
        delete(Job)
        .where(Job.last_seen_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    deleted = session.execute(stmt).rowcount or 0
    session.commit()
    return deleted
