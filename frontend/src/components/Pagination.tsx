import Link from "next/link";

import { buildHref } from "@/lib/filters";

type Props = { page: number; lastPage: number; q: string; days?: number };

export function Pagination({ page, lastPage, q, days }: Props) {
  if (lastPage <= 1) return null;
  const off = "btn h-9 px-3.5 text-zinc-600";

  return (
    <nav
      aria-label="Pagination"
      className="flex items-center justify-between gap-4"
    >
      {page > 1 ? (
        <Link
          href={buildHref({ q, days, page: page - 1 })}
          className="btn btn-ghost h-9 px-3.5"
          rel="prev"
        >
          ← Previous
        </Link>
      ) : (
        <span className={off}>← Previous</span>
      )}
      <span className="text-xs text-zinc-500">
        Page <span className="font-medium text-zinc-200">{page}</span> of{" "}
        {lastPage}
      </span>
      {page < lastPage ? (
        <Link
          href={buildHref({ q, days, page: page + 1 })}
          className="btn btn-ghost h-9 px-3.5"
          rel="next"
        >
          Next →
        </Link>
      ) : (
        <span className={off}>Next →</span>
      )}
    </nav>
  );
}
