"""Pydantic schemas: the exact JSON shapes the API sends to the frontend."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    url: str
    title: str
    company_name: str
    location: str
    workplace: str
    employment_type: str | None
    salary_text: str | None
    posted_at: datetime | None

    @field_validator("posted_at", mode="after")
    @classmethod
    def assume_utc(cls, value: datetime | None) -> datetime | None:
        """SQLite drops time zones; every stored datetime is UTC, so say so."""
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @field_serializer("job_id")
    def job_id_as_text(self, value: int) -> str:
        """The frontend contract types job_id as a string."""
        return str(value)


class JobDetail(JobSummary):
    company_url: str | None
    description_html: str


class JobListResponse(BaseModel):
    items: list[JobSummary]
    total: int
    page: int
    page_size: int


class AddedJob(BaseModel):
    job_id: str
    title: str
    company_name: str
    added_at: datetime

    @field_validator("job_id", mode="before")
    @classmethod
    def id_as_text(cls, value: object) -> object:
        return str(value)


class CrawlProgress(BaseModel):
    """Live view of the dashboard crawl (None until the first dashboard crawl)."""

    phase: str
    detail: str
    started_at: datetime | None
    finished_at: datetime | None
    result: str | None
    method: str
    max_pages: int
    pages_done: int
    max_new: int
    jobs_new: int
    jobs_refreshed: int
    jobs_rejected: int
    recent_jobs: list[AddedJob]


class CrawlStatus(BaseModel):
    is_running: bool
    progress: CrawlProgress | None = None
    total_jobs: int
    last_run_at: datetime | None
    last_run_status: str | None


class CrawlStarted(BaseModel):
    started: bool
    message: str
