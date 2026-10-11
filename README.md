# HB Crawler
A polite crawler that collects **fully remote** startup jobs from
[startup.jobs](https://startup.jobs/remote-jobs), stores them in SQLite, serves
them through a FastAPI backend and shows them in a Next.js job board.
Runs locally only.
## Requirements
Python 3.11+, Node.js 20.9+, Git. Versions are pinned on both sides
(`backend/requirements*.txt`, `frontend/package.json` + `package-lock.json`).
## Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env # then set CONTACT_EMAIL
python -m pytest # 31 tests must pass
python -m app.cli crawl --max-pages 1 --max-new 5 # first small crawl
uvicorn app.main:app --reload # API on http://127.0.0.1:8000/docs
```
## Frontend
```bash
cd frontend
npm ci # exact versions from package-lock.json
cp .env.local.example .env.local
npm run dev # http://localhost:3000
```
## Rules the crawler follows
robots.txt is read before every run, one request every 10 seconds, honest
User-Agent with a contact email, stops on HTTP 403/429, never touches login,
apply or paid "Plus" pages. If the website blocks the crawler, it never tries to
disguise itself: with `STARTUP_JOBS_API_KEY` set it switches to the official
Startup Jobs API instead. Every job links back to startup.jobs.
Re-publishing startup.jobs data for commercial purposes needs their permission.