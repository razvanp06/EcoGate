import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // In dev, forward /api/* to the local Azure Functions host (func start).
  server: {
    proxy: {
      "/api": "http://localhost:7071",
    },
  },
});
