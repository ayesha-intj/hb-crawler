import Link from "next/link";

import { CompanyAvatar } from "@/components/CompanyAvatar";
import { BriefcaseIcon, ExternalIcon, MapPinIcon } from "@/components/icons";
import { formatDate, formatPosted } from "@/lib/format";
import type { JobSummary } from "@/lib/types";

// One row of the job list. The whole row opens the detail page; the external
// link (startup.jobs) sits above the stretched link so it stays clickable.
export function JobCard({ job }: { job: JobSummary }) {
  return (
    <li className="group relative flex gap-4 px-5 py-4 transition-colors hover:bg-white/[0.025]">
      <CompanyAvatar name={job.company_name} />

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="truncate text-[0.95rem] font-medium text-zinc-100">
              <Link
                href={`/jobs/${job.job_id}`}
                className="outline-none after:absolute after:inset-0 focus-visible:underline"
              >
                {job.title}
              </Link>
            </h2>
            <p className="mt-0.5 truncate text-sm text-zinc-400">
              {job.company_name}
            </p>
          </div>
          <time
            dateTime={job.posted_at ?? undefined}
            title={formatDate(job.posted_at)}
            className="shrink-0 pt-0.5 text-xs text-zinc-500"
          >
            {formatPosted(job.posted_at)}
          </time>
        </div>

        <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-zinc-400">
          {job.location && (
            <span className="inline-flex items-center gap-1.5">
              <MapPinIcon className="size-3.5 text-zinc-500" />
              {job.location}
            </span>
          )}
          {job.employment_type && (
            <span className="inline-flex items-center gap-1.5">
              <BriefcaseIcon className="size-3.5 text-zinc-500" />
              {job.employment_type}
            </span>
          )}
          {job.salary_text && (
            <span className="rounded-md bg-emerald-300/[0.08] px-1.5 py-0.5 font-medium text-emerald-200/90">
              {job.salary_text}
            </span>
          )}
          <a
            href={job.url}
            target="_blank"
            rel="noopener"
            className="relative z-10 ml-auto inline-flex items-center gap-1 text-zinc-500 transition-colors hover:text-zinc-200"
          >
            startup.jobs
            <ExternalIcon className="size-3.5" />
          </a>
        </div>
      </div>
    </li>
  );
}
