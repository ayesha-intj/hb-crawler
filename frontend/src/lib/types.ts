// Frontend contract. Mirrors backend/app/schemas.py (job_id is serialised as text).

export interface JobSummary {
  job_id: string;
  title: string;
  company_name: string;
  location?: string | null;
  employment_type?: string | null;
  salary_text?: string | null;
  posted_at?: string | null;
  url: string;
}

export interface JobDetail extends JobSummary {
  company_url: string | null;
  description_html: string;
}

export interface JobListResponse {
  items: JobSummary[];
  total: number;
  page_size: number;
  page: number;
}

export interface AddedJob {
  job_id: string;
  title: string;
  company_name: string;
  added_at: string;
}

/** Live view of the dashboard crawl; null until the first dashboard crawl. */
export interface CrawlProgress {
  phase: "starting" | "listing" | "checking" | "api" | "stopping" | "finished";
  detail: string;
  started_at: string | null;
  finished_at: string | null;
  result: "success" | "blocked" | "failed" | "cancelled" | "interrupted" | null;
  /** "api_fallback" when the website refused the crawler and the official API was used. */
  method: "crawler" | "api_fallback";
  max_pages: number;
  pages_done: number;
  max_new: number;
  jobs_new: number;
  jobs_refreshed: number;
  jobs_rejected: number;
  recent_jobs: AddedJob[];
}

export interface CrawlStatus {
  is_running: boolean;
  last_run_at: string | null;
  last_run_status: string | null;
  total_jobs: number;
  progress?: CrawlProgress | null;
}
