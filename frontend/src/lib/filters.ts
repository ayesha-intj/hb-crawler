// URL-driven filters: every view is a shareable link such as /?q=python&days=7&page=2

export const DATE_RANGES = [
  { label: "All Time", days: undefined },
  { label: "Past 3 Days", days: 3 },
  { label: "Past 7 Days", days: 7 },
  { label: "Past 14 Days", days: 14 },
] as const;

const ALLOWED_DAYS: readonly number[] = [3, 7, 14];

export type Filters = { q?: string; days?: number; page?: number };

export function parseDays(value?: string): number | undefined {
  const days = Number(value);
  return ALLOWED_DAYS.includes(days) ? days : undefined;
}

export function parsePage(value?: string): number {
  return Math.max(1, Math.floor(Number(value)) || 1);
}

export function buildHref({ q, days, page }: Filters): string {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (days) params.set("days", String(days));
  if (page && page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `/?${query}` : "/";
}
