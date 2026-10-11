"""All /api endpoints. Each function is one URL the frontend can call."""

from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import (
    CrawlStarted,
    CrawlStatus,
    JobDetail,
    JobListResponse,
    JobSummary,
)
from app.services import crawl_runner, job_queries

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
        is_running=crawl_runner.is_running(session),
        progress=crawl_runner.progress.snapshot(),
        total_jobs=job_queries.total_jobs(session),
        last_run_at=last_run_at,
        last_run_status=run.status if run else None,
    )


@router.post("/crawl", response_model=CrawlStarted, status_code=202)
def start_crawl(background_tasks: BackgroundTasks, session: SessionDep) -> CrawlStarted:
    """Start one polite crawl in the background. 409 if one is already running."""
    if not crawl_runner.try_start(session):
        raise HTTPException(status_code=409, detail="A crawl is already running")
    background_tasks.add_task(crawl_runner.run_and_release)
    return CrawlStarted(started=True, message="Crawl started")


@router.post("/crawl/stop", response_model=CrawlStarted, status_code=202)
def stop_crawl() -> CrawlStarted:
    """Ask the dashboard crawl to stop. 409 if no dashboard crawl is running."""
    if not crawl_runner.request_stop():
        raise HTTPException(status_code=409, detail="No dashboard crawl is running")
    return CrawlStarted(started=False, message="Stopping")


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    session: SessionDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Search title, company, location")
    ] = None,
    days: Annotated[
        int | None, Query(ge=1, le=365, description="Posted within N days")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> JobListResponse:
    rows, total = job_queries.list_jobs(
        session, q, page, page_size, posted_within_days=days
    )
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
