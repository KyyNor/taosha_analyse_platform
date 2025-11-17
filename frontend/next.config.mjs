const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:50020/api/:path*"
      }
    ];
  }
};

export default nextConfig;