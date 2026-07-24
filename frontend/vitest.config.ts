import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      // Mirror tsconfig.json "paths": { "@/*": ["./*"] } (R1-7)
      "@": path.resolve(__dirname, "."),
    },
  },
});
