import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// All AI calls go through the FastAPI backend. Vite dev server proxies
// /api and /media to localhost:8000 so the frontend has no CORS dance.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/media": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
