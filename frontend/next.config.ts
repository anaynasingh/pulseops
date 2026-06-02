import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow images from avatar APIs
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "api.dicebear.com" },
    ],
  },
  // Transpile packages if needed
  transpilePackages: [],
};

export default nextConfig;
