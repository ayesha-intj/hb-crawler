"""Read-only queries used by the API routes."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import CrawlRun, Job


def list_jobs(
    session: Session, query: str | None, page: int, page_size: int
) -> tuple[list[Job], int]:
    """Return one page of jobs (newest first) and the total number of matches."""
    stmt = select(Job)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(pattern),
                Job.company_name.ilike(pattern),
                Job.location.ilike(pattern),
            )
        )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.scalars(
        stmt.order_by(Job.posted_at.desc().nulls_last(), Job.job_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def get_job(session: Session, job_id: int) -> Job | None:
    return session.get(Job, job_id)


def total_jobs(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Job)) or 0


def last_run(session: Session) -> CrawlRun | None:
    return session.scalar(select(CrawlRun).order_by(CrawlRun.id.desc()).limit(1))
