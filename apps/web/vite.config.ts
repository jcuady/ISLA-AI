import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The UI is served by the KALIX local core in production. In dev, Vite proxies
// API calls to the loopback backend so the browser still only ever talks to
// 127.0.0.1 - the air-gap claim holds in both modes.
export default defineConfig({
  plugins: [react()],
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
});