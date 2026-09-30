import type { NextConfig } from "next";

// Static export: the app is a client-side PWA talking to the ARMOR backend, so it
// can be served from any static host (or by the backend itself for the offline
// demo). Detail pages use query parameters instead of dynamic routes.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
