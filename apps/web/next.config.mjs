import bundleAnalyzer from '@next/bundle-analyzer';

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Existing Next.js config (none previously defined, but ready for extension)
};

export default withBundleAnalyzer(nextConfig);
