const DAY_MS = 24 * 60 * 60 * 1000;

export function formatDate(value?: string | null): string {
  if (!value) return "Date unknown";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

/** "Today", "Yesterday", "5 days ago", or the date for older posts. */
export function formatPosted(value?: string | null): string {
  if (!value) return "Date unknown";
  const days = Math.floor((Date.now() - new Date(value).getTime()) / DAY_MS);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  return formatDate(value);
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "never";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
