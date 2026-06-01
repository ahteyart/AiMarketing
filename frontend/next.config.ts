import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.canva.com" },
      { protocol: "https", hostname: "*.canvausercontent.com" },
      { protocol: "http", hostname: "localhost" },
    ],
  },
};

export default nextConfig;
