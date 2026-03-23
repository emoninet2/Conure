import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Load ALL env vars from current folder
  const env = loadEnv(mode, __dirname, "");

  const frontendPort = env.FRONTEND_PORT || "5173";
  const backendPort = env.BACKEND_PORT || "8001";
  const apiHost = env.VITE_API_HOST || "http://localhost";

  const apiBase = `${apiHost}:${backendPort}`;

  console.log("Frontend port:", frontendPort);
  console.log("Backend API:", apiBase);

  return {
    plugins: [react()],

    server: {
      port: Number(frontendPort),
    },

    define: {
      "import.meta.env.VITE_API_BASE": JSON.stringify(apiBase),
    },
  };
});