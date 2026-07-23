const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  experimental: {
    serverComponentsExternalPackages: ['stripe']
  },
  webpack: (config) => {
    // Force Webpack to resolve single instance of React & React-dom
    config.resolve.alias = {
      ...config.resolve.alias,
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
    };
    // config.resolve.modules.push(path.resolve('../../node_modules'));
    return config;
  }
}

module.exports = nextConfig
