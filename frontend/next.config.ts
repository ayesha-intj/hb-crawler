import type { NextConfig } from "next";

// Verified with next@16.4.0 (pinned in package.json).
const API_BASE_URL = process.env.HB_API_BASE_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,

  // `npm run dev` only serves its live-reload and client scripts to localhost.
  // Opening the app through a network address such as http://192.168.1.9:3000
  // blocks them, React never starts in the browser, and buttons do nothing.
  // These patterns allow private home/office network addresses (development only).
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.16.*.*", "*.local"],

  // Browser code (the crawler panel) calls /api/... on the frontend's own origin;
  // Next.js forwards the request to FastAPI. Same origin = no CORS in the browser.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_BASE_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
