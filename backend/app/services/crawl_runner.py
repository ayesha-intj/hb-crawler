"""Runs one crawl in the background for the dashboard (start, stop, live progress).

Only one crawl may run at a time. In this process a lock guarantees it; a crawl
started from the CLI is detected through its `crawl_runs` row.
"""

import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crawler.fetcher import PoliteFetcher
from app.crawler.pipeline import prune_stale_jobs, run_crawl
from app.crawler.progress import CrawlProgress
from app.database import SessionLocal
from app.models import CrawlRun

log = logging.getLogger(__name__)

_lock = threading.Lock()
_stop_event = threading.Event()
progress = CrawlProgress()  # read by GET /api/status
# A "running" row older than this is a crashed run, not an active one.
STALE_RUN_AFTER = timedelta(hours=1)


def _cli_run_active(session: Session) -> bool:
    cutoff = datetime.now(UTC) - STALE_RUN_AFTER
    stmt = select(CrawlRun.id).where(
        CrawlRun.status == "running", CrawlRun.started_at > cutoff
    )
    return session.scalar(stmt.limit(1)) is not None


def is_running(session: Session) -> bool:
    return _lock.locked() or _cli_run_active(session)


def try_start(session: Session) -> bool:
    """Reserve the single crawl slot. Return False if a crawl is already active."""
    if _cli_run_active(session) or not _lock.acquire(blocking=False):
        return False
    _stop_event.clear()
    settings = get_settings()
    progress.start(settings.max_listing_pages, settings.max_new_jobs)
    return True


def request_stop() -> bool:
    """Ask the running crawl to stop. The polite wait is interruptible, so it stops at once."""
    if not _lock.locked():
        return False
    _stop_event.set()
    progress.set_phase("stopping", "Finishing the current request, then stopping")
    return True


def run_and_release() -> None:
    """Background task: one polite crawl with the .env limits, then free the slot."""
    settings = get_settings()
    try:
        with (
            PoliteFetcher(
                settings.user_agent,
                settings.crawl_delay_seconds,
                settings.request_timeout_seconds,
                stop_event=_stop_event,
            ) as fetcher,
            SessionLocal() as session,
        ):
            result = run_crawl(session, settings, fetcher, progress)
            prune_stale_jobs(session, settings.job_retention_days)
        log.info(
            "Dashboard crawl finished: %s, %d new job(s)", result.status, result.new
        )
    except Exception:  # never leave the lock held after an unexpected error
        log.exception("Dashboard crawl crashed")
        progress.finish("failed", "Unexpected error, see the backend log.")
    finally:
        _lock.release()
