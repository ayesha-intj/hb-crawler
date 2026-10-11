import Link from "next/link";

import { buildHref, DATE_RANGES } from "@/lib/filters";

// Segmented control. Changing the range keeps the search text and resets to page 1.
export function DateFilterTabs({ q, days }: { q: string; days?: number }) {
  return (
    <nav
      aria-label="Posted date"
      className="inline-flex shrink-0 rounded-lg border border-white/[0.08] bg-black/20 p-0.5"
    >
      {DATE_RANGES.map((range) => {
        const active = range.days === days;
        return (
          <Link
            key={range.label}
            href={buildHref({ q, days: range.days })}
            aria-current={active ? "page" : undefined}
            className={`whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300/60 ${
              active
                ? "bg-white/[0.09] text-zinc-100 shadow-sm"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {range.label}
          </Link>
        );
      })}
    </nav>
  );
}
