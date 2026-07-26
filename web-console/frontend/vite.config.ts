import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const apiTarget = process.env.VITE_DEV_API_TARGET ?? "http://127.0.0.1:8787";

function assertLoopbackTarget(value: string): string {
  const parsed = new URL(value);
  const loopback = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost";
  if (parsed.protocol !== "http:" || !loopback || parsed.username || parsed.password) {
    throw new Error("VITE_DEV_API_TARGET must be an HTTP loopback URL.");
  }
  return value;
}

const safeApiTarget = assertLoopbackTarget(apiTarget);

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: safeApiTarget,
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
    proxy: {
      "/api": {
        target: safeApiTarget,
        changeOrigin: false,
      },
    },
  },
});
