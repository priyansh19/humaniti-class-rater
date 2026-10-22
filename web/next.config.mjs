/** @type {import('next').NextConfig} */
const nextConfig = {
  // Transcript-only fallback runs as a Vercel Python function (api/index.py) under /api/py/*.
  // In production vercel.json routes /api/py/* to the function; in dev proxy to a local uvicorn.
  async rewrites() {
    return process.env.NODE_ENV === "development" ? [{ source: "/api/py/:path*", destination: "http://127.0.0.1:8000/api/py/:path*" }] : [];
  },
  poweredByHeader: false,
};
export default nextConfig;
