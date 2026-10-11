"""Live progress of one crawl run, shared between the crawl thread and the API.

The crawl thread writes, the /api/status endpoint reads. A lock keeps every read
consistent. The CLI passes no progress object, so it is unaffected.
"""

import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

MAX_RECENT_JOBS = 25


@dataclass
class AddedJob:
    job_id: int
    title: str
    company_name: str
    added_at: datetime


@dataclass
class ProgressSnapshot:
    phase: str = "idle"  # starting | listing | checking | api | stopping | finished
    detail: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: str | None = None  # success | blocked | failed | cancelled | interrupted
    method: str = "crawler"  # crawler | api_fallback
    max_pages: int = 0
    pages_done: int = 0
    max_new: int = 0
    jobs_new: int = 0
    jobs_refreshed: int = 0
    jobs_rejected: int = 0
    recent_jobs: list[AddedJob] = field(default_factory=list)


class CrawlProgress:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = ProgressSnapshot()

    def start(self, max_pages: int, max_new: int) -> None:
        with self._lock:
            self._data = ProgressSnapshot(
                phase="starting",
                detail="Reading robots.txt",
                started_at=datetime.now(UTC),
                max_pages=max_pages,
                max_new=max_new,
            )

    def set_phase(self, phase: str, detail: str = "") -> None:
        with self._lock:
            if self._data.phase != "stopping" or phase == "finished":
                self._data.phase, self._data.detail = phase, detail

    def switch_to_api(self, max_api_pages: int, reason: str) -> None:
        """The website blocked the crawler: further counts come from the official API."""
        with self._lock:
            self._data.method = "api_fallback"
            self._data.pages_done = 0
            self._data.max_pages = max_api_pages
            if self._data.phase != "stopping":
                self._data.phase, self._data.detail = "api", reason

    def page_done(self) -> None:
        with self._lock:
            self._data.pages_done += 1

    def add_refreshed(self, count: int) -> None:
        with self._lock:
            self._data.jobs_refreshed += count

    def add_rejected(self) -> None:
        with self._lock:
            self._data.jobs_rejected += 1

    def add_job(self, job_id: int, title: str, company_name: str) -> None:
        with self._lock:
            self._data.jobs_new += 1
            self._data.recent_jobs.insert(
                0, AddedJob(job_id, title, company_name, datetime.now(UTC))
            )
            del self._data.recent_jobs[MAX_RECENT_JOBS:]

    def finish(self, result: str, detail: str = "") -> None:
        with self._lock:
            self._data.phase, self._data.result = "finished", result
            self._data.detail = detail
            self._data.finished_at = datetime.now(UTC)

    def snapshot(self) -> dict | None:
        with self._lock:
            if self._data.started_at is None:
                return None
            return asdict(self._data)