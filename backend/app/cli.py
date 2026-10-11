"""Command-line entry point of the crawler.

python -m app.cli crawl
python -m app.cli crawl --max-pages 1 --max-new 5
python -m app.cli inspect <url>
python -m app.cli export-csv --output jobs.csv
python -m app.cli stats
"""

import argparse
import csv
import logging
import sys

from sqlalchemy import select

from app.config import DATA_DIR, get_settings
from app.crawler.fetcher import PoliteFetcher
from app.crawler.pipeline import prune_stale_jobs, run_crawl
from app.database import SessionLocal, init_db
from app.models import CrawlRun, Job

log = logging.getLogger("hb_crawler")

CSV_COLUMNS = [
    "job_id",
    "title",
    "company_name",
    "location",
    "employment_type",
    "salary_text",
    "posted_at",
    "url",
]


def command_crawl(args: argparse.Namespace) -> int:
    overrides = {
        key: value
        for key, value in {
            "max_listing_pages": args.max_pages,
            "max_new_jobs": args.max_new,
            "crawl_delay_seconds": args.delay,
        }.items()
        if value is not None
    }
    settings = get_settings().model_copy(update=overrides)
    if settings.crawl_delay_seconds < 5:
        log.error("Please keep the delay at 5 seconds or more. Be polite!")
        return 2
    log.info(
        "Crawling up to %d listing page(s), %d new job(s), one request every %.0fs",
        settings.max_listing_pages,
        settings.max_new_jobs,
        settings.crawl_delay_seconds,
    )
    with (
        PoliteFetcher(
            settings.user_agent,
            settings.crawl_delay_seconds,
            settings.request_timeout_seconds,
        ) as fetcher,
        SessionLocal() as session,
    ):
        result = run_crawl(session, settings, fetcher)
        removed = prune_stale_jobs(session, settings.job_retention_days)
        log.info(
            "Run %s via %s: pages=%d new=%d refreshed=%d rejected=%d removed=%d %s",
            result.status.upper(),
            result.method,
            result.pages,
            result.new,
            result.refreshed,
            result.rejected,
            removed,
            result.message,
        )
        return 0 if result.status == "success" else 1


def command_inspect(args: argparse.Namespace) -> int:
    settings = get_settings()
    folder = DATA_DIR / "pages"  # absolute: same folder whatever your working directory
    folder.mkdir(parents=True, exist_ok=True)
    with PoliteFetcher(settings.user_agent, settings.crawl_delay_seconds) as fetcher:
        fetcher.load_robots()
        html = fetcher.get_html(args.url)
        if html is None:
            log.error("Could not download %s", args.url)
            return 1
        target = folder / (
            args.url.rstrip("/").rsplit("/", 1)[-1].replace("?", "_") or "page"
        )
        target = target.with_suffix(".html")
        target.write_text(html, encoding="utf-8")
        log.info("Saved %s (%d characters). Open it in your editor.", target, len(html))
        return 0


def command_export_csv(args: argparse.Namespace) -> int:
    with SessionLocal() as session:
        rows = session.scalars(select(Job).order_by(Job.posted_at.desc())).all()
        with open(args.output, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for job in rows:
                writer.writerow(
                    {column: getattr(job, column) for column in CSV_COLUMNS}
                )
        log.info("Exported %d jobs to %s", len(rows), args.output)
        return 0


def command_stats(args: argparse.Namespace) -> int:
    with SessionLocal() as session:
        total = len(session.scalars(select(Job.job_id)).all())
        runs = session.scalars(
            select(CrawlRun).order_by(CrawlRun.id.desc()).limit(5)
        ).all()
        print(f"Remote jobs in database: {total}\nLast runs:")
        for run in runs:
            print(
                f" #{run.id} {run.started_at:%Y-%m-%d %H:%M} {run.status:<11} {run.method:<12} "
                f"pages={run.pages_crawled} new={run.jobs_new} "
                f"refreshed={run.jobs_refreshed} rejected={run.jobs_rejected}"
            )
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="HB Crawler")
    sub = parser.add_subparsers(dest="command", required=True)

    crawl = sub.add_parser("crawl", help="crawl startup.jobs remote jobs")
    crawl.add_argument(
        "--max-pages", type=int, help="listing pages to read (default from .env)"
    )
    crawl.add_argument("--max-new", type=int, help="new job pages to download")
    crawl.add_argument("--delay", type=float, help="seconds between requests (>= 5)")
    crawl.set_defaults(handler=command_crawl)

    inspect = sub.add_parser(
        "inspect", help="download one page to data/pages/ for study"
    )
    inspect.add_argument("url")
    inspect.set_defaults(handler=command_inspect)

    export = sub.add_parser("export-csv", help="write all jobs to a CSV file")
    export.add_argument("--output", default="jobs.csv")
    export.set_defaults(handler=command_export_csv)

    stats = sub.add_parser("stats", help="show job count and recent runs")
    stats.set_defaults(handler=command_stats)

    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = build_parser().parse_args()
    init_db()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
