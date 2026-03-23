import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  console.log("vite config loaded from:", __dirname);

  const env = loadEnv(mode, __dirname, "");
  const frontendPort = parseInt(env.FRONTEND_PORT ?? "5173", 10);
  const backendPort = parseInt(env.BACKEND_PORT ?? "8000", 10);
  const apiHost = env.VITE_API_HOST ?? "http://localhost";
  const apiBase = `${apiHost}:${backendPort}`;

  console.log("FRONTEND_PORT raw =", env.FRONTEND_PORT);
  console.log("frontendPort =", frontendPort);
  console.log("backendPort =", backendPort);
  console.log("apiBase =", apiBase);

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: frontendPort,
      strictPort: true,
    },
    define: {
      "import.meta.env.VITE_API_BASE": JSON.stringify(apiBase),
    },
  };
});