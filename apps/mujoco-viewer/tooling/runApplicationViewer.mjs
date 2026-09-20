/** 共通launcher専用。Viteのlisten完了を、その起動のreadiness fileへ記録する。 */
import { createServer } from "vite";
import { writeFile, rename } from "node:fs/promises";

const [configFile, host, portText, readyFile, digest] = process.argv.slice(2);
const port = Number(portText);
if (!configFile || !host || !readyFile || !/^[0-9a-f]{64}$/.test(digest ?? "") ||
    !Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error("invalid application viewer invocation");
}
const server = await createServer({ configFile, server: { host, port, strictPort: true, open: false } });
let closing = false;
const close = async () => {
  if (closing) return;
  closing = true;
  await server.close();
};
process.once("SIGINT", () => void close());
process.once("SIGTERM", () => void close());
try {
  await server.listen();
  await writeFile(`${readyFile}.tmp`, JSON.stringify({ pid: process.pid, configuration_sha256: digest }), "utf8");
  await rename(`${readyFile}.tmp`, readyFile);
  server.printUrls();
} catch (error) {
  await close();
  throw error;
}
