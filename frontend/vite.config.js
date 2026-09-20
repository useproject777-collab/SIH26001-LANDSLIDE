import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Disable Vite HMR websocket to avoid localhost websocket 400 errors in this setup.
    // The page can still be refreshed normally with Ctrl+R.
    hmr: false,
  },
});
