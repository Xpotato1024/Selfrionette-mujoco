import { defineConfig } from "vite";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(appRoot, "../..");

export default defineConfig({
  root: repoRoot,
  appType: "mpa",
  publicDir: resolve(appRoot, "public"),
  server: {
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
});
