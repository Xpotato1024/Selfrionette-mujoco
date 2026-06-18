import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const viewerRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(viewerRoot, "../..");
const repoAssetsRoot = path.join(repoRoot, "assets");

function fastArmAssetMiddleware() {
  return {
    name: "fast-arm-assets",
    configureServer(server) {
      server.middlewares.use("/assets", (request, response, next) => {
        const requestUrl = request.url ?? "";
        const requestedPath = decodeURIComponent(requestUrl.split("?")[0] ?? "");
        const assetPath = path.resolve(repoAssetsRoot, `.${requestedPath}`);

        if (!assetPath.startsWith(repoAssetsRoot + path.sep)) {
          response.statusCode = 403;
          response.end("Forbidden");
          return;
        }

        if (!fs.existsSync(assetPath) || !fs.statSync(assetPath).isFile()) {
          next();
          return;
        }

        response.setHeader("Content-Type", assetPath.endsWith(".stl") ? "model/stl" : "application/octet-stream");
        fs.createReadStream(assetPath).pipe(response);
      });
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [react(), fastArmAssetMiddleware()],
});
