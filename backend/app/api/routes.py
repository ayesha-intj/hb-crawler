"""All /api endpoints. Each function is one URL the frontend can call."""

from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import CrawlStatus, JobDetail, JobListResponse, JobSummary
from app.services import job_queries

router = APIRouter(prefix="/api")
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/status", response_model=CrawlStatus)
def crawl_status(session: SessionDep) -> CrawlStatus:
    run = job_queries.last_run(session)
    last_run_at = run.started_at if run else None
    if last_run_at is not None and last_run_at.tzinfo is None:
        last_run_at = last_run_at.replace(tzinfo=UTC)  # SQLite drops time zones
    return CrawlStatus(
        total_jobs=job_queries.total_jobs(session),
        last_run_at=last_run_at,
        last_run_status=run.status if run else None,
    )


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    session: SessionDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Search title, company, location")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobListResponse:
    rows, total = job_queries.list_jobs(session, q, page, page_size)
    return JobListResponse(
        items=[JobSummary.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: int, session: SessionDep) -> JobDetail:
    job = job_queries.get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail.model_validate(job)
