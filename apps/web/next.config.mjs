import { withSentryConfig } from '@sentry/nextjs/config';
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Existing Next.js config (none previously defined, but ready for extension)
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
};

export default withSentryConfig(withBundleAnalyzer(nextConfig), {
  silent: false,
  org: process.env.SENTRY_ORG || "hiron",
  project: process.env.SENTRY_PROJECT || "hiron-web",
  widenClientFileUpload: true,
  transpileClientSDK: true,
  hideSourceMaps: true,
});
