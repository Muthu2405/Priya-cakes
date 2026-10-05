import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api is proxied to Django so no CORS or env setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
