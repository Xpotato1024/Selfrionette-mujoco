import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Plugin } from "vite";

const appRoot = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(appRoot, "../..");
const adapterResources = resolve(
  repoRoot,
  "src/selfrionette/plugins/robots/fast_arm/adapter/resources",
);
const coreModelResources = resolve(
  repoRoot,
  "src/selfrionette/plugins/robots/fast_arm/core/src/fast_arm_core/resources/model",
);
const fastArmPackageResources = new Map<string, string>([
  ["/mujoco/fast_arm/scene.xml", resolve(adapterResources, "mujoco/scene.xml")],
  ["/mujoco/fast_arm/viewer-profile.json", resolve(adapterResources, "viewer-profile.json")],
  ["/mujoco/fast_arm/fixtures/fast_arm_sweep_x_qpos.json", resolve(adapterResources, "fixtures/fast_arm_sweep_x_qpos.json")],
  ["/mujoco/fast_arm/arm.xml", resolve(coreModelResources, "arm.xml")],
  ...[
    "BaseLink.stl",
    "SholderLink1.stl",
    "SholderLink2.stl",
    "UpperArmLink.stl",
    "ForeArmLink.stl",
  ].map((name) => [
    `/mujoco/fast_arm/meshes/${name}`,
    resolve(coreModelResources, "meshes", name),
  ] as const),
]);

function fastArmPackageResourcePlugin(): Plugin {
  return {
    name: "fast-arm-package-resources",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const requestPath = new URL(request.url ?? "/", "http://viewer.local").pathname;
        const sourcePath = fastArmPackageResources.get(requestPath);
        if (sourcePath === undefined) {
          next();
          return;
        }
        response.statusCode = 200;
        response.end(readFileSync(sourcePath));
      });
    },
    generateBundle() {
      for (const [publicPath, sourcePath] of fastArmPackageResources) {
        this.emitFile({
          type: "asset",
          fileName: publicPath.slice(1),
          source: readFileSync(sourcePath),
        });
      }
    },
  };
}

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
  plugins: [fastArmPackageResourcePlugin(), react()],
});
