import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "HB Crawler | Remote startup jobs",
  description: "Fully remote startup jobs crawled from startup.jobs.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-dvh text-zinc-300 antialiased">
        <div className="mx-auto flex min-h-dvh max-w-6xl flex-col px-4 sm:px-6 lg:px-8">
          <header className="flex items-center justify-between border-b border-white/[0.06] py-4">
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 rounded-md text-sm font-semibold text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300/60"
            >
              <span className="grid size-7 place-items-center rounded-md bg-[var(--color-accent-strong)] text-[0.65rem] font-bold text-white">
                HB
              </span>
              HB Crawler
            </Link>
            <span className="text-xs text-zinc-500">
              Remote jobs · local dashboard
            </span>
          </header>

          <main className="flex-1 py-8">{children}</main>

          <footer className="border-t border-white/[0.06] py-5 text-left text-xs text-zinc-500">
            Data sourced from{" "}
            <a
              href="https://startup.jobs"
              target="_blank"
              rel="noopener"
              className="text-zinc-300 underline-offset-4 hover:underline"
            >
              startup.jobs
            </a>
          </footer>
        </div>
      </body>
    </html>
  );
}
