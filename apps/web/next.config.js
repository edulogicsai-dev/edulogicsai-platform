const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  experimental: {
    serverComponentsExternalPackages: ['stripe']
  },
  webpack: (config) => {
    config.resolve.modules.push(path.resolve('../../node_modules'));
    return config;
  }
}

module.exports = nextConfig
