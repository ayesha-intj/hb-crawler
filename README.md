# HB Crawler

A job board of **fully remote** startup jobs, collected from
[startup.jobs](https://startup.jobs/remote-jobs) by a polite crawler.

- **Backend:** Python crawler + FastAPI + SQLite
- **Frontend:** Next.js 16 + Tailwind CSS 4

## Features

- **Fully remote only:** hybrid and on-site jobs are filtered out.
- **Polite crawling:**
  - respects robots.txt;
  - sends one request every 10 seconds;
  - stops if the site blocks it.
- **Official API fallback:** if the website blocks the crawler, it uses the official
  Startup Jobs API instead.
- **Job board:** search, date filters, pagination and job detail pages.
- **Live crawler panel:** start, stop, progress, and the jobs added in real time.

## Requirements

Python 3.11+, Node.js 20.9+

## Setup

**Backend**, from `backend/`:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

**Frontend**, from `frontend/`:

```bash
npm ci
copy .env.local.example .env.local   # macOS/Linux: cp .env.local.example .env.local
```

## Run

Use two terminals.

```bash
# backend/ (virtual environment active)
uvicorn app.main:app --reload

# frontend/
npm run dev
```

Open **http://localhost:3000** and click **Run live crawler**.

To crawl from the terminal instead: `python -m app.cli crawl`, run from `backend/`.

## Configuration

Settings live in `backend/.env`:

| Variable | Default | Meaning |
|---|---|---|
| `CRAWL_DELAY_SECONDS` | `10` | Seconds between requests (minimum 5) |
| `MAX_LISTING_PAGES` | `3` | Listing pages read per run |
| `MAX_NEW_JOBS` | `50` | New jobs saved per run |

## Data source

Job data comes from [startup.jobs](https://startup.jobs). Every listing links back to
its original page. Their [terms](https://startup.jobs/terms) allow re-publishing
the data for non-commercial use only.