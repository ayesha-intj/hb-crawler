"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AlertIcon, CheckIcon, PlayIcon, StopIcon } from "@/components/icons";
import type { CrawlProgress, CrawlStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;

type Tone = "neutral" | "active" | "warning" | "success" | "danger";

const CHIP: Record<Tone, string> = {
  neutral: "bg-white/[0.06] text-zinc-300",
  active: "bg-indigo-400/15 text-indigo-200",
  warning: "bg-amber-400/15 text-amber-200",
  success: "bg-emerald-400/15 text-emerald-200",
  danger: "bg-rose-400/15 text-rose-200",
};

const RESULT: Record<string, { tone: Tone; label: string; text: string }> = {
  success: { tone: "success", label: "Completed", text: "Sync complete." },
  cancelled: {
    tone: "warning",
    label: "Stopped",
    text: "Stopped by you. Jobs saved so far are kept.",
  },
  blocked: {
    tone: "danger",
    label: "Blocked",
    text: "startup.jobs refused the crawler (403/429). Wait before retrying, or set STARTUP_JOBS_API_KEY.",
  },
  interrupted: {
    tone: "warning",
    label: "Interrupted",
    text: "The crawl was interrupted.",
  },
  failed: {
    tone: "danger",
    label: "Failed",
    text: "The crawl failed. The backend terminal shows why.",
  },
};

function formatDuration(ms: number): string {
  const seconds = Math.max(0, Math.round(ms / 1000));
  const minutes = Math.floor(seconds / 60);
  return minutes > 0 ? `${minutes} min ${seconds % 60} s` : `${seconds} s`;
}

/** Turn a failed HTTP answer into an instruction the user can act on. */
function explainHttpError(status: number): string {
  if (status === 404) {
    return "The /api/crawl route was not found. Restart uvicorn (backend), then stop and restart `npm run dev`: changes to next.config.ts only apply after a restart.";
  }
  if (status >= 500) {
    return "The backend is not reachable on port 8000. Start it in backend/ with: uvicorn app.main:app --reload";
  }
  return `The backend answered HTTP ${status}.`;
}

function Meter({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const percent = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="tabular-nums text-zinc-200">
          {value} <span className="text-zinc-500">/ {max}</span>
        </span>
      </div>
      <div
        className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.06]"
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div
          className="h-full rounded-full bg-indigo-400/80 transition-[width] duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function Counter({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "success";
}) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-black/20 px-3 py-2">
      <div
        className={`text-lg font-semibold tabular-nums ${tone === "success" ? "text-emerald-300" : "text-zinc-100"}`}
      >
        {value}
      </div>
      <div className="text-[0.7rem] text-zinc-500">{label}</div>
    </div>
  );
}

export function CrawlerPanel({
  initialStatus,
}: {
  initialStatus: CrawlStatus;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<CrawlStatus>(initialStatus);
  const [pending, setPending] = useState<"start" | "stop" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState<number | null>(null); // set only in the browser (no hydration mismatch)
  const lastNewCount = useRef(initialStatus.progress?.jobs_new ?? 0);

  const progress: CrawlProgress | null = status.progress ?? null;
  const running = status.is_running;
  const dashboardRun =
    running && progress !== null && progress.phase !== "finished";
  const terminalRun = running && !dashboardRun; // started with `python -m app.cli crawl`

  // Poll /api/status every 2 s while a crawl runs; refresh the job list when jobs are added.
  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok) throw new Error(explainHttpError(response.status));
        const next = (await response.json()) as CrawlStatus;
        if (cancelled) return;
        setStatus(next);
        setError(null);
        const added = next.progress?.jobs_new ?? 0;
        if (added !== lastNewCount.current || !next.is_running) {
          lastNewCount.current = added;
          router.refresh(); // re-render the job list (Server Components) with the new rows
        }
      } catch (problem) {
        if (!cancelled)
          setError(
            problem instanceof Error
              ? problem.message
              : "Lost contact with the backend.",
          );
      }
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [running, router]);

  // Elapsed-time clock, ticking once per second while running.
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);

  async function refreshStatus() {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error(explainHttpError(response.status));
    setStatus((await response.json()) as CrawlStatus);
  }

  async function startCrawl() {
    setPending("start");
    setError(null);
    try {
      const response = await fetch("/api/crawl", { method: "POST" });
      if (!response.ok && response.status !== 409) {
        setError(explainHttpError(response.status));
        return;
      }
      lastNewCount.current = 0;
      await refreshStatus(); // shows the running state immediately, polling takes over
    } catch {
      setError(
        "No answer from the server. Are `npm run dev` and uvicorn both running?",
      );
    } finally {
      setPending(null);
    }
  }

  async function stopCrawl() {
    setPending("stop");
    setError(null);
    try {
      const response = await fetch("/api/crawl/stop", { method: "POST" });
      if (response.status === 409) {
        setError(
          "This crawl was started from the terminal: stop it there with Ctrl+C.",
        );
        return;
      }
      if (!response.ok) {
        setError(explainHttpError(response.status));
        return;
      }
      await refreshStatus();
    } catch {
      setError("No answer from the server.");
    } finally {
      setPending(null);
    }
  }

  // ---- header chip
  let chip: { tone: Tone; label: string } = { tone: "neutral", label: "Idle" };
  if (dashboardRun) {
    chip =
      progress.phase === "stopping"
        ? { tone: "warning", label: "Stopping" }
        : { tone: "active", label: "Running" };
  } else if (terminalRun) {
    chip = { tone: "active", label: "Running (terminal)" };
  } else if (progress?.result) {
    chip = RESULT[progress.result] ?? chip;
  }

  const startedAt = progress?.started_at
    ? Date.parse(progress.started_at)
    : null;
  const finishedAt = progress?.finished_at
    ? Date.parse(progress.finished_at)
    : null;
  const elapsed =
    startedAt === null
      ? null
      : finishedAt !== null && !dashboardRun
        ? finishedAt - startedAt
        : now
          ? now - startedAt
          : null;
  const outcome = !running && progress?.result ? RESULT[progress.result] : null;
  const usedApi = progress?.method === "api_fallback";

  return (
    <section className="surface p-5" aria-labelledby="crawler-title">
      <div className="flex items-center justify-between gap-3">
        <h2 id="crawler-title" className="text-sm font-semibold text-zinc-100">
          Live crawler
        </h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.7rem] font-medium ${CHIP[chip.tone]}`}
        >
          {chip.tone === "active" && (
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-indigo-300 opacity-75" />
              <span className="relative inline-flex size-1.5 rounded-full bg-indigo-300" />
            </span>
          )}
          {chip.label}
        </span>
      </div>

      <p className="mt-1.5 text-xs leading-relaxed text-zinc-500">
        Reads the startup.jobs remote listing politely: one request every 10
        seconds, limits from <code className="text-zinc-400">backend/.env</code>
        .
      </p>

      {error && (
        <div
          role="alert"
          className="mt-4 flex gap-2 rounded-lg border border-rose-400/20 bg-rose-400/[0.06] p-3 text-xs leading-relaxed text-rose-200"
        >
          <AlertIcon className="mt-0.5 size-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {terminalRun && (
        <p className="mt-4 rounded-lg border border-white/[0.06] bg-black/20 p-3 text-xs text-zinc-400">
          A crawl started from the terminal is running. Its progress is shown
          there; press Ctrl+C in that terminal to stop it.
        </p>
      )}

      {progress && !terminalRun && (
        <div className="mt-4 space-y-4" aria-live="polite">
          {dashboardRun && (
            <div className="rounded-lg border border-white/[0.06] bg-black/20 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-zinc-200">
                  {progress.phase === "stopping"
                    ? "Stopping…"
                    : progress.phase === "checking"
                      ? "Checking job"
                      : progress.phase === "api"
                        ? "Official API"
                        : "Working"}
                </span>
                <span className="tabular-nums text-zinc-500">
                  {elapsed !== null ? formatDuration(elapsed) : "…"}
                </span>
              </div>
              <p
                className="mt-1 truncate text-xs text-zinc-400"
                title={progress.detail}
              >
                {progress.detail || "Starting…"}
              </p>
            </div>
          )}

          {outcome && (
            <div
              className={`flex gap-2 rounded-lg border p-3 text-xs leading-relaxed ${
                outcome.tone === "success"
                  ? "border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200"
                  : outcome.tone === "warning"
                    ? "border-amber-400/20 bg-amber-400/[0.06] text-amber-200"
                    : "border-rose-400/20 bg-rose-400/[0.06] text-rose-200"
              }`}
            >
              {outcome.tone === "success" ? (
                <CheckIcon className="mt-0.5 size-3.5 shrink-0" />
              ) : (
                <AlertIcon className="mt-0.5 size-3.5 shrink-0" />
              )}
              <span>
                {outcome.text} {progress.jobs_new} new job
                {progress.jobs_new === 1 ? "" : "s"} added
                {usedApi ? " via the official API" : ""}
                {elapsed !== null ? ` in ${formatDuration(elapsed)}` : ""}.
              </span>
            </div>
          )}

          {usedApi && (
            <p className="rounded-lg border border-white/[0.06] bg-black/20 p-3 text-xs leading-relaxed text-zinc-400">
              The website refused the crawler (HTTP 403/429), so jobs{" "}
              {dashboardRun ? "are coming" : "came"} from the official Startup
              Jobs API instead of the listing pages.
            </p>
          )}

          <div className="space-y-3">
            <Meter
              label={usedApi ? "API pages" : "Listing pages"}
              value={progress.pages_done}
              max={progress.max_pages}
            />
            <Meter
              label="New jobs"
              value={progress.jobs_new}
              max={progress.max_new}
            />
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Counter label="Added" value={progress.jobs_new} tone="success" />
            <Counter label="Known" value={progress.jobs_refreshed} />
            <Counter label="Not remote" value={progress.jobs_rejected} />
          </div>
        </div>
      )}

      <div className="mt-5">
        {dashboardRun ? (
          <button
            type="button"
            onClick={stopCrawl}
            disabled={pending !== null || progress?.phase === "stopping"}
            className="btn btn-danger h-10 w-full"
          >
            <StopIcon className="size-4" />
            {progress?.phase === "stopping" ? "Stopping…" : "Stop crawl"}
          </button>
        ) : (
          <button
            type="button"
            onClick={startCrawl}
            disabled={pending !== null || running}
            className="btn btn-primary h-10 w-full"
          >
            <PlayIcon className="size-4" />
            {pending === "start" ? "Starting…" : "Run live crawler"}
          </button>
        )}
      </div>

      {progress && progress.recent_jobs.length > 0 && !terminalRun && (
        <div className="mt-5 border-t border-white/[0.06] pt-4">
          <h3 className="text-xs font-medium text-zinc-400">
            Added to the database{dashboardRun ? " (live)" : " in the last run"}
          </h3>
          <ul className="mt-2 max-h-72 space-y-0.5 overflow-y-auto pr-1">
            {progress.recent_jobs.map((job) => (
              <li key={job.job_id}>
                <Link
                  href={`/jobs/${job.job_id}`}
                  className="block rounded-md px-2 py-1.5 transition-colors hover:bg-white/[0.04]"
                >
                  <span className="block truncate text-xs text-zinc-200">
                    {job.title}
                  </span>
                  <span className="block truncate text-[0.7rem] text-zinc-500">
                    {job.company_name}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
