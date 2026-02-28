import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Transpile the Stream SDK so Next.js can process its modules
  transpilePackages: ["@stream-io/video-react-sdk"],
};

export default nextConfig;
