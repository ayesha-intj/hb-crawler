import { Suspense } from "react";

import { CrawlerPanel } from "@/components/CrawlerPanel";
import { DateFilterTabs } from "@/components/DateFilterTabs";
import { ClockIcon, DatabaseIcon, TrendIcon } from "@/components/icons";
import { JobCard } from "@/components/JobCard";
import { Pagination } from "@/components/Pagination";
import { SearchBar } from "@/components/SearchBar";
import { fetchJobs, fetchStatus } from "@/lib/api";
import { parseDays, parsePage } from "@/lib/filters";
import { formatDateTime } from "@/lib/format";

type SearchParams = Promise<{ q?: string; page?: string; days?: string }>;

const LAST_RUN_LABEL: Record<string, string> = {
  success: "completed",
  cancelled: "stopped",
  blocked: "blocked",
  failed: "failed",
  interrupted: "interrupted",
  running: "running",
};

export default function HomePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-50 sm:text-[1.75rem]">
          Remote startup jobs
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm text-zinc-400">
          Fully remote roles collected from startup.jobs. Hybrid and on-site
          roles are filtered out before they reach the database.
        </p>
      </header>

      {/* Cache Components: everything that calls the backend sits inside <Suspense>. */}
      <Suspense fallback={<StatsSkeleton />}>
        <Stats />
      </Suspense>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <aside className="order-first lg:sticky lg:top-6 lg:order-last">
          <Suspense fallback={<div className="surface h-64 animate-pulse" />}>
            <Crawler />
          </Suspense>
        </aside>

        <Suspense fallback={<ResultsSkeleton />}>
          <JobResults searchParams={searchParams} />
        </Suspense>
      </div>
    </div>
  );
}

async function Stats() {
  const [status, lastWeek] = await Promise.all([
    fetchStatus(),
    fetchJobs({ days: 7, pageSize: 1 }),
  ]);
  const lastRun = status.last_run_status
    ? (LAST_RUN_LABEL[status.last_run_status] ?? status.last_run_status)
    : null;
  const tiles = [
    {
      icon: DatabaseIcon,
      label: "Jobs in database",
      value: String(status.total_jobs),
    },
    {
      icon: TrendIcon,
      label: "Posted in the last 7 days",
      value: String(lastWeek.total),
    },
    {
      icon: ClockIcon,
      label: lastRun ? `Last crawl · ${lastRun}` : "Last crawl",
      value: formatDateTime(status.last_run_at),
    },
  ];
  return (
    <dl className="grid gap-3 sm:grid-cols-3">
      {tiles.map(({ icon: Icon, label, value }) => (
        <div
          key={label}
          className="surface flex items-center gap-3.5 px-4 py-3.5"
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-white/[0.05] text-zinc-400 ring-1 ring-inset ring-white/[0.06]">
            <Icon className="size-4" />
          </span>
          <div className="min-w-0">
            <dt className="truncate text-xs text-zinc-500">{label}</dt>
            <dd className="truncate text-base font-semibold tabular-nums text-zinc-100">
              {value}
            </dd>
          </div>
        </div>
      ))}
    </dl>
  );
}

async function Crawler() {
  const status = await fetchStatus();
  return <CrawlerPanel initialStatus={status} />;
}

async function JobResults({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const q = params.q?.trim() ?? "";
  const days = parseDays(params.days);
  const page = parsePage(params.page);

  const data = await fetchJobs({ q, page, days });
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <section className="min-w-0 space-y-4" aria-label="Job listings">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <SearchBar q={q} days={days} />
        <DateFilterTabs q={q} days={days} />
      </div>

      <div className="surface overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
          <p className="text-xs text-zinc-400" aria-live="polite">
            <span className="font-medium text-zinc-200">{data.total}</span>{" "}
            {data.total === 1 ? "job" : "jobs"}
            {q && (
              <>
                {" "}
                matching <span className="text-zinc-200">“{q}”</span>
              </>
            )}
          </p>
          <p className="text-xs text-zinc-500">Newest first</p>
        </div>

        {data.items.length > 0 ? (
          <ul className="divide-y divide-white/[0.05]">
            {data.items.map((job) => (
              <JobCard key={job.job_id} job={job} />
            ))}
          </ul>
        ) : (
          <div className="px-5 py-14 text-center">
            <p className="text-sm text-zinc-300">
              No jobs match these filters.
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Try another search, a wider date range, or run the crawler.
            </p>
          </div>
        )}
      </div>

      <Pagination
        page={Math.min(page, lastPage)}
        lastPage={lastPage}
        q={q}
        days={days}
      />
    </section>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-3" aria-hidden="true">
      {[0, 1, 2].map((key) => (
        <div key={key} className="surface h-[4.25rem] animate-pulse" />
      ))}
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="space-y-4" aria-hidden="true">
      <div className="h-10 animate-pulse rounded-lg bg-white/[0.04]" />
      <div className="surface h-96 animate-pulse" />
    </div>
  );
}
