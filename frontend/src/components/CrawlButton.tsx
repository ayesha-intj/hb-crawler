"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AlertIcon, CheckIcon, RefreshIcon } from "@/components/icons";
import type { CrawlStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;

type Phase = "idle" | "starting" | "running" | "done" | "error";

function finishedMessage(status: CrawlStatus): { phase: Phase; text: string } {
  switch (status.last_run_status) {
    case "success":
      return {
        phase: "done",
        text: `Sync complete! ${status.total_jobs} jobs on the board.`,
      };
    case "blocked":
      return {
        phase: "error",
        text: "The site blocked the crawler (403/429). Check the backend log.",
      };
    case "interrupted":
      return { phase: "error", text: "The crawl was interrupted." };
    default:
      return {
        phase: "error",
        text: "The crawl failed. Check the backend log.",
      };
  }
}

export function CrawlButton({ initialStatus }: { initialStatus: CrawlStatus }) {
  const router = useRouter();
  const [isRunning, setIsRunning] = useState(initialStatus.is_running);
  const [phase, setPhase] = useState<Phase>(
    initialStatus.is_running ? "running" : "idle",
  );
  const [message, setMessage] = useState(
    initialStatus.is_running ? "Crawler active…" : "",
  );

  async function startCrawl() {
    if (isRunning) return; // the button is disabled too; this guards double clicks
    setIsRunning(true);
    setPhase("starting");
    setMessage("Starting crawler…");
    try {
      const response = await fetch("/api/crawl", { method: "POST" });
      if (response.status === 409) {
        setPhase("running");
        setMessage("A crawl is already running. Following it…");
        return;
      }
      if (!response.ok) throw new Error(`Backend answered ${response.status}`);
      setPhase("running");
      setMessage("Crawler active… one polite request every 10 seconds.");
    } catch (error) {
      setIsRunning(false);
      setPhase("error");
      setMessage(
        error instanceof Error ? error.message : "Could not start the crawler.",
      );
    }
  }

  // Poll /api/status every 2 s while a crawl runs. Starts only once the POST has answered.
  useEffect(() => {
    if (phase !== "running") return;
    let cancelled = false;

    const timer = setInterval(async () => {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok || cancelled) return;
        const status = (await response.json()) as CrawlStatus;
        if (cancelled || status.is_running) return;

        const result = finishedMessage(status);
        setIsRunning(false);
        setPhase(result.phase);
        setMessage(result.text);
        router.refresh(); // re-render the Server Components with the new jobs
      } catch {
        // Temporary network problem: keep polling.
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [phase, router]);

  return (
    <div className="flex flex-col items-start gap-2 sm:items-end">
      <button
        type="button"
        onClick={startCrawl}
        disabled={isRunning}
        aria-busy={isRunning}
        className="btn-primary h-11 gap-2 px-5 text-sm"
      >
        <RefreshIcon className={`size-4 ${isRunning ? "animate-spin" : ""}`} />
        {isRunning ? "Crawling…" : "Run Live Crawler"}
      </button>
      <p
        role="status"
        aria-live="polite"
        className={`flex min-h-5 items-center gap-1.5 text-xs ${
          phase === "error"
            ? "text-rose-300"
            : phase === "done"
              ? "text-emerald-300"
              : "text-slate-400"
        }`}
      >
        {phase === "running" && (
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-cyan-400" />
          </span>
        )}
        {phase === "done" && <CheckIcon className="size-3.5" />}
        {phase === "error" && <AlertIcon className="size-3.5" />}
        {message}
      </p>
    </div>
  );
}
