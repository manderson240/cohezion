import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the Turbopack workspace root to THIS app. Without it, Next infers the root from the
  // nearest lockfile and picks ~/package-lock.json (three lockfiles compete: ~, repo pnpm-lock,
  // and this app's). Resolution then starts at src/web and `@import "tailwindcss"` in globals.css
  // fails with "Can't resolve 'tailwindcss'", which surfaces as the React Client Manifest
  // global-error.js crash (the error boundary failing to render the real error).
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
