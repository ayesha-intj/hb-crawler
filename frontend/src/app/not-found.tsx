import Link from "next/link";

export default function NotFound() {
  return (
    <div className="surface mx-auto max-w-lg space-y-4 p-8 text-center">
      <h1 className="text-xl font-semibold text-zinc-100">Job not found</h1>
      <p className="text-sm text-zinc-400">
        It may have expired or been removed by its source.
      </p>
      <Link href="/" className="btn btn-ghost h-10 px-5">
        ← Back to all jobs
      </Link>
    </div>
  );
}
