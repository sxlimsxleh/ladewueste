import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The web app calls /api/...; in development Vite forwards that to the FastAPI server.
// The browser only ever talks to the Vite origin, so this works locally and in Codespaces.
const API_TARGET = process.env.LADEWUESTE_API ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname },
  },
  server: {
    port: 5173,
    // Codespaces serves the dev server under *.app.github.dev; Vite rejects unknown hosts by default.
    allowedHosts: [".app.github.dev"],
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  // MapLibre + deck.gl are ~2.3 MB minified (665 kB gzipped) on their own; that is the price of
  // a WebGL map, not a bundling mistake, so the default 500 kB warning is raised.
  build: { chunkSizeWarningLimit: 2500 },
  test: {
    include: ["src/**/*.test.ts"],
  },
});
