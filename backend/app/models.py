"""ORM models: the tables of the HB Crawler database."""

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Job(Base):
    """One remote job from startup.jobs. The primary key is the site's own job id."""

    __tablename__ = "jobs"
    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    url: Mapped[str] = mapped_column(String(500), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    company_name: Mapped[str] = mapped_column(String(200), index=True)
    company_url: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(300), default="")
    workplace: Mapped[str] = mapped_column(String(20), default="remote")
    employment_type: Mapped[str | None] = mapped_column(String(40))
    salary_text: Mapped[str | None] = mapped_column(String(120))
    description_html: Mapped[str] = mapped_column(Text, default="")
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CrawlRun(Base):
    """One execution of the crawler, kept for monitoring and debugging."""

    __tablename__ = "crawl_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    method: Mapped[str] = mapped_column(
        String(20), default="crawler"
    )  # crawler | api_fallback
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    jobs_refreshed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_rejected: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)
