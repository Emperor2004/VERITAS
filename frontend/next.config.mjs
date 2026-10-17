/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Standalone output for Docker production builds — bundles only required
  // node_modules into .next/standalone, reducing image size by ~90%.
  output: 'standalone',

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.BACKEND_API_URL
          ? `${process.env.BACKEND_API_URL}/api/:path*`
          : 'http://127.0.0.1:8000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
