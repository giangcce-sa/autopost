/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Agents/connectors chỉ chạy ở server; bỏ qua bundle phía client.
  serverExternalPackages: ["@anthropic-ai/sdk", "@prisma/client"],
};

export default nextConfig;
