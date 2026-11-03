/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: relative by default (works from any sub-path); CI sets MPSIM_BASE=/<repo-name>/ for GitHub Pages.
// Mode "live" (npm run dev:api) makes the UI talk to the local API instead of the static synthetic bundle
// (see src/data/provider.ts; VITE_DATA_SOURCE=api|static and ?source= override it).
export default defineConfig(() => ({
  base: process.env.MPSIM_BASE ?? "./",
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  preview: { host: "127.0.0.1", port: 4173 },
  build: { outDir: "dist", sourcemap: false, emptyOutDir: true },
  test: { environment: "jsdom", include: ["src/__tests__/**/*.test.{ts,tsx}"] },
}));
