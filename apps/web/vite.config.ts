import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev the browser calls /api/*, which is proxied to FastAPI on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: process.env.API_URL ?? "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});
