import { SearchIcon } from "@/components/icons";

// Plain GET form: submitting loads /?q=...&days=..., so search needs no client JavaScript.
export function SearchBar({ q, days }: { q: string; days?: number }) {
  return (
    <form action="/" role="search" className="flex flex-1 gap-2">
      <label htmlFor="q" className="sr-only">
        Search jobs
      </label>
      <div className="relative flex-1">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500" />
        <input
          id="q"
          name="q"
          type="search"
          defaultValue={q}
          placeholder="Search jobs or companies"
          className="field h-10 w-full pl-9 pr-3 text-sm"
        />
      </div>
      {days && <input type="hidden" name="days" value={days} />}
      <button type="submit" className="btn btn-ghost h-10 px-4">
        Search
      </button>
    </form>
  );
}
