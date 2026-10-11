"""Pydantic schemas: the exact JSON shapes the API sends to the frontend."""

from datetime import UTC, datetime
from pydantic import BaseModel, ConfigDict, field_validator


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


class JobDetail(JobSummary):
    company_url: str | None
    description_html: str


class JobListResponse(BaseModel):
    items: list[JobSummary]
    total: int
    page: int
    page_size: int


class CrawlStatus(BaseModel):
    total_jobs: int
    last_run_at: datetime | None
    last_run_status: str | None
