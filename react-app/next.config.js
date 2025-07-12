/** @type {import('next').NextConfig} */
const nextConfig = {
  // basePath: '/share',
  reactStrictMode: true,
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'cdn-icons-png.flaticon.com',
        pathname: '**',
      },
    ],
  },
  // Configure for development access from different IPs
  ...(process.env.NODE_ENV === 'development' && {
    assetPrefix: process.env.NEXT_PUBLIC_REACT_URL || '',
    webpack: (config, { dev, isServer }) => {
      if (dev && !isServer) {
        config.devtool = 'cheap-module-source-map';
        // Configure webpack dev server for cross-origin access
        config.devServer = {
          ...config.devServer,
          allowedHosts: 'all',
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
            'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization',
          },
        };
      }
      return config;
    },
  }),
}

// Only apply static export settings for production builds
if (process.env.NODE_ENV === 'production') {
  nextConfig.output = 'export';
  nextConfig.distDir = 'out';
}

module.exports = nextConfig
