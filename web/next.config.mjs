/** @type {import('next').NextConfig} */
const nextConfig = {
  // Transcript-only fallback runs as a Vercel Python function (api/index.py) under /api/py/*.
  async rewrites() {
    return [{
      source: "/api/py/:path*",
      destination: process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000/api/py/:path*" : "/api/",
    }];
  },
  poweredByHeader: false,
};
export default nextConfig;
