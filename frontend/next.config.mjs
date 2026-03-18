const nextConfig = {
  basePath: '/taosha',
  assetPrefix: '/taosha',
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:50011/api/:path*"
      }
    ];
  }
};

export default nextConfig;