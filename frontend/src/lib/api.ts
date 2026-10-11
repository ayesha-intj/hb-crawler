// Server-side client for the FastAPI backend (used by Server Components).
// Browser code calls the relative /api/... path instead, proxied by next.config.ts.
import type { CrawlStatus, JobDetail, JobListResponse } from "./types";

const API_BASE_URL = process.env.HB_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${API_BASE_URL}. Is uvicorn running?`,
    );
  }
  if (!response.ok) {
    throw new ApiError(
      `Backend answered ${response.status} for ${path}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export function fetchJobs({
  q = "",
  page = 1,
  days,
  pageSize = 20,
}: {
  q?: string;
  page?: number;
  days?: number;
  pageSize?: number;
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (q) params.set("q", q);
  if (days) params.set("days", String(days));
  return getJson<JobListResponse>(`/api/jobs?${params}`);
}

export async function fetchJob(id: string): Promise<JobDetail | null> {
  try {
    return await getJson<JobDetail>(`/api/jobs/${encodeURIComponent(id)}`);
  } catch (error) {
    // 404: unknown job. 422: the id in the URL is not a number.
    if (
      error instanceof ApiError &&
      (error.status === 404 || error.status === 422)
    )
      return null;
    throw error;
  }
}

export function fetchStatus() {
  return getJson<CrawlStatus>("/api/status");
}
