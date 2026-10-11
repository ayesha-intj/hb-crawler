"use client";

// Shown when a Server Component throws (for example, the backend is not running).
// In production Next.js hides the real message, so we add a helpful hint.
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  const message =
    process.env.NODE_ENV === "development"
      ? error.message
      : "The job data could not be loaded. Check that the backend is running on port 8000.";
  return (
    <div className="surface mx-auto max-w-lg space-y-4 p-8 text-center">
      <h1 className="text-xl font-semibold text-zinc-100">
        Something went wrong
      </h1>
      <p className="text-sm text-zinc-400">{message}</p>
      <button onClick={reset} className="btn btn-primary h-10 px-5">
        Try again
      </button>
    </div>
  );
}
