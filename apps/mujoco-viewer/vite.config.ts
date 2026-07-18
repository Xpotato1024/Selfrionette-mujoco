import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { createViewerPackageResourcePlugin } from "./tooling/viewerPackageResources.js";

const appRoot = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(appRoot, "../..");
export default defineConfig({
  root: repoRoot,
  base: "./",
  appType: "mpa",
  publicDir: false,
  server: {
    open: "/apps/mujoco-viewer/",
    fs: {
      allow: [repoRoot, appRoot],
    },
  },
  build: {
    outDir: resolve(appRoot, "dist"),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(appRoot, "index.html"),
    },
  },
  plugins: [createViewerPackageResourcePlugin(repoRoot), react()],
});
