import type { NextConfig } from "next";

// Set GITHUB_PAGES=true in CI to enable the /philmont-maps base path.
const basePath = process.env.GITHUB_PAGES === "true" ? "/philmont-maps" : "";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
  // Expose to client components via process.env.NEXT_PUBLIC_BASE_PATH
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

export default nextConfig;
