"""Fallback source: the official Startup Jobs API, used only when the website
blocks the crawler (HTTP 403/429) and an API key is configured.

Why this and not a "stealth" headless browser? A 403/429 is the site saying no.
Disguising a bot to get past it breaks the ground rules of this project and the
site's terms. The API is the channel startup.jobs offers for automated access.

API facts (https://api.startup.jobs/v1/openapi.json, checked October 2026):
bearer key, 20 requests/minute, last 14 days, max 50 jobs per page, cursor
pagination (`next_cursor` -> `starting_after`), `workplace_type=remote` filter.
Job ids are the same numbers as in the website URLs, so rows never duplicate.
"""

import logging
import threading
from dataclasses import dataclass

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.crawler.fetcher import CrawlCancelled
from app.crawler.progress import CrawlProgress
from app.crawler.text import clean_html, parse_datetime, squash
from app.crawler.urls import canonical_job_url, job_id_from_url
from app.models import Job

log = logging.getLogger(__name__)

API_URL = "https://api.startup.jobs/v1/jobs"
PAGE_SIZE = 50
REQUEST_INTERVAL_SECONDS = 4.0  # 20 requests/minute allowed; one every 4 s stays below


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


def run_api_fallback(
    session: Session,
    settings: Settings,
    seen_at,
    progress: CrawlProgress | None = None,
    stop_event: threading.Event | None = None,
) -> ApiResult:
    """Fetch recent remote jobs from the API and store the new ones."""
    progress = progress or CrawlProgress()
    stop_event = stop_event or threading.Event()
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
            # Interruptible pause: the dashboard Stop button ends the wait at once.
            if stop_event.wait(REQUEST_INTERVAL_SECONDS if page > 1 else 0):
                raise CrawlCancelled("Stopped by user")
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
            progress.page_done()
            jobs = [
                job
                for raw in payload.get("data") or []
                if (job := job_from_api(raw, seen_at)) is not None
            ]
            rejected = len(payload.get("data") or []) - len(jobs)
            result.rejected += rejected
            for _ in range(rejected):
                progress.add_rejected()

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
                    progress.add_refreshed(1)
                elif result.new < settings.max_new_jobs:
                    session.add(job)
                    result.new += 1
                    progress.add_job(job.job_id, job.title, job.company_name)
                    log.info(
                        "[API %d] %s - %s", result.new, job.title, job.company_name
                    )
            if known:
                session.execute(
                    update(Job)
                    .where(Job.job_id.in_(known))
                    .values(last_seen_at=seen_at)
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
