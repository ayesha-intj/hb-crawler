"""One crawl run: listing pages -> new job pages -> remote check -> database.

Flow
  1. Read robots.txt (refuse to crawl without it).
  2. Walk /remote-jobs page 1, 2, ... (newest first) up to MAX_LISTING_PAGES.
  3. Known jobs: only refresh `last_seen_at` (no extra request).
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
from app.crawler.fetcher import (
    BlockedError,
    CrawlCancelled,
    CrawlerError,
    PoliteFetcher,
)
from app.crawler.job_parser import parse_job_page
from app.crawler.listing_parser import ListingItem, has_next_page, parse_listing
from app.crawler.progress import CrawlProgress
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
    session: Session,
    settings: Settings,
    fetcher: PoliteFetcher,
    progress: CrawlProgress | None = None,
) -> CrawlResult:
    progress = progress or CrawlProgress()  # the CLI passes none: a throw-away tracker
    progress.start(settings.max_listing_pages, settings.max_new_jobs)
    run = CrawlRun(started_at=utc_now(), status="running")
    session.add(run)
    session.commit()

    result = CrawlResult()
    seen_at = utc_now()
    try:
        fetcher.load_robots()
        for page in range(1, settings.max_listing_pages + 1):
            progress.set_phase("listing", f"Reading listing page {page}")
            html = fetcher.get_html(listing_page_url(page))
            if html is None:
                break
            result.pages += 1
            progress.page_done()
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
                    progress.add_rejected()
                    continue
                if result.new >= settings.max_new_jobs:
                    continue
                progress.set_phase("checking", f"{item.title} - {item.company_name}")
                detail_html = fetcher.get_html(item.url)
                if detail_html is None:
                    continue
                new_on_page += 1
                if save_new_job(session, item, detail_html, seen_at):
                    result.new += 1
                    progress.add_job(item.job_id, item.title, item.company_name)
                    log.info(
                        "[%d/%d] %s - %s",
                        result.new,
                        settings.max_new_jobs,
                        item.title,
                        item.company_name,
                    )
                else:
                    result.rejected += 1
                    progress.add_rejected()

            if known:
                progress.add_refreshed(len(known))
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
    except CrawlCancelled:
        result.status = "cancelled"
        result.message = "Stopped by user. Jobs saved so far are kept."
    except BlockedError as error:
        result.status = "blocked"
        result.message = f"{error}. Crawler stopped. Do NOT retry with tricks."
        if settings.startup_jobs_api_key:
            _switch_to_api(
                session, settings, result, seen_at, progress, fetcher.stop_event, error
            )
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

    progress.finish(result.status, result.message)
    run.finished_at = utc_now()
    run.status = result.status
    run.method = result.method
    run.pages_crawled, run.jobs_new = result.pages, result.new
    run.jobs_refreshed, run.jobs_rejected = result.refreshed, result.rejected
    run.message = result.message or None
    session.commit()
    return result


def _switch_to_api(
    session: Session,
    settings: Settings,
    result: CrawlResult,
    seen_at,
    progress: CrawlProgress,
    stop_event,
    error: BlockedError,
) -> None:
    """The website said no: use the official API (key required) for this run."""
    log.warning(
        "Website blocked the crawler; switching to the official Startup Jobs API."
    )
    progress.switch_to_api(
        settings.api_max_pages,
        f"Website refused the crawler ({error}). Using the official API.",
    )
    try:
        api = run_api_fallback(session, settings, seen_at, progress, stop_event)
    except CrawlCancelled:
        session.commit()
        result.method, result.status = "api_fallback", "cancelled"
        result.message = "Stopped by user. Jobs saved so far are kept."
        return
    except ApiError as api_error:
        result.message += f" API fallback failed: {api_error}"
        return
    result.method, result.status = "api_fallback", "success"
    result.pages += api.pages
    result.new += api.new
    result.refreshed += api.refreshed
    result.rejected += api.rejected
    result.message = (
        f"The website refused the crawler ({error}); {api.new} new job(s) came from the "
        "official Startup Jobs API instead."
    )


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
