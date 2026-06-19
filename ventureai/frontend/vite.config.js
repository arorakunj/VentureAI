import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        // Proxy API calls to the FastAPI backend during development so the
        // frontend can call /evaluate, /status, /memo without CORS friction.
        proxy: {
            "/evaluate": "http://localhost:8000",
            "/status": "http://localhost:8000",
            "/memo": "http://localhost:8000",
            "/ws": {
                target: "ws://localhost:8000",
                ws: true,
            },
        },
    },
});
