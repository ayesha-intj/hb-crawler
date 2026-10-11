import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Badge } from "@/components/Badge";
import { CompanyAvatar } from "@/components/CompanyAvatar";
import {
  BanknoteIcon,
  BriefcaseIcon,
  BuildingIcon,
  CalendarIcon,
  ExternalIcon,
  GlobeIcon,
  MapPinIcon,
} from "@/components/icons";
import { fetchJob } from "@/lib/api";
import { formatDate, formatPosted } from "@/lib/format";

type Params = Promise<{ id: string }>;

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const job = await fetchJob((await params).id);
  if (!job) return { title: "Job not found | HB Crawler" };
  return {
    title: `${job.title} at ${job.company_name} | HB Crawler`,
    // The content belongs to startup.jobs: point search engines to the original.
    alternates: { canonical: job.url },
  };
}

export default function JobPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<div className="surface h-96 animate-pulse" />}>
      <JobDetails params={params} />
    </Suspense>
  );
}

async function JobDetails({ params }: { params: Params }) {
  const job = await fetchJob((await params).id);
  if (!job) notFound();

  return (
    <article className="mx-auto max-w-3xl space-y-5">
      <Link
        href="/"
        className="inline-flex text-sm text-zinc-400 hover:text-zinc-100"
      >
        ← All jobs
      </Link>

      <header className="surface space-y-5 p-6 sm:p-8">
        <div className="flex items-start gap-4">
          <CompanyAvatar name={job.company_name} size="lg" />
          <div className="min-w-0">
            <h1 className="text-xl font-semibold tracking-tight text-zinc-50 sm:text-2xl">
              {job.title}
            </h1>
            <p className="mt-1 text-sm text-zinc-400">{job.company_name}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge icon={BuildingIcon} label="Company" tone="accent">
            {job.company_url ? (
              <a
                href={job.company_url}
                target="_blank"
                rel="noopener"
                className="hover:underline"
              >
                {job.company_name}
              </a>
            ) : (
              job.company_name
            )}
          </Badge>
          <Badge icon={GlobeIcon} label="Workplace">
            Remote
          </Badge>
          {job.location && (
            <Badge icon={MapPinIcon} label="Location">
              {job.location}
            </Badge>
          )}
          {job.employment_type && (
            <Badge icon={BriefcaseIcon} label="Type">
              {job.employment_type}
            </Badge>
          )}
          {job.salary_text && (
            <Badge icon={BanknoteIcon} label="Salary" tone="success">
              {job.salary_text}
            </Badge>
          )}
          <Badge icon={CalendarIcon} label="Posted">
            <span title={formatDate(job.posted_at)}>
              {formatPosted(job.posted_at)}
            </span>
          </Badge>
        </div>
        {/* Applications always happen on startup.jobs. */}
        <a
          href={job.url}
          target="_blank"
          rel="noopener"
          className="btn btn-primary h-10 px-4"
        >
          View and apply on startup.jobs
          <ExternalIcon className="size-4" />
        </a>
      </header>

      <section className="surface p-6 sm:p-8" aria-label="Job description">
        {/* Sanitised with nh3 by the backend before storage. */}
        <div
          className="job-description"
          dangerouslySetInnerHTML={{ __html: job.description_html }}
        />
      </section>
    </article>
  );
}
