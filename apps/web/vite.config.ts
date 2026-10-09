// defineConfig comes from vitest/config, not vite, so the `test` block below is
// typed. Importing it from "vite" would fail typecheck with an unknown property.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

// The UI is served by the Isla AI local core in production. In dev, Vite proxies
// API calls to the loopback backend so the browser still only ever talks to
// 127.0.0.1 - the air-gap claim holds in both modes.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // shadcn convention: "@/components/ui/..." resolves to src/components/ui
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});