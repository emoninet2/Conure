// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react'

// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react()],
// })


import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default ({ mode }) => {
  // Conure/uix/frontend/conure -> Conure
  const rootDir = path.resolve(__dirname, "../../..");

  // Load ONLY VITE_* vars from Conure/.env* files
  const env = loadEnv(mode, rootDir, "VITE_");

  return defineConfig({
    plugins: [react()],
    define: {
      // Make it available exactly like normal Vite env vars
      "import.meta.env.VITE_API_BASE": JSON.stringify(env.VITE_API_BASE),
    },
  });
};