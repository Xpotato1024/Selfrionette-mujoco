export {};

declare const process: {
  cwd(): string;
};

const fsModule = (await Function("return import('node:fs')")()) as Promise<{
  readFileSync(path: string, options: string): string;
}>;
const pathModule = (await Function("return import('node:path')")()) as Promise<{
  resolve(...segments: string[]): string;
}>;

const { readFileSync } = await fsModule;
const { resolve } = await pathModule;

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function readIndexHtml(): string {
  const indexHtmlPath = resolve(process.cwd(), "index.html");
  return readFileSync(indexHtmlPath, "utf-8");
}

function readFastArmMeshSource(): string {
  const sourcePath = resolve(process.cwd(), "src", "wasm-scene", "mujocoWasmLoader.ts");
  return readFileSync(sourcePath, "utf-8");
}

function testViteEntrypointIncludesMainTsxAndStlLoader(): void {
  const html = readIndexHtml();
  const sceneRendererSource = readFastArmMeshSource();

  assert(
    html.includes('<script type="module" src="/apps/mujoco-viewer/src/main.tsx"></script>'),
    "index.html should load the Vite entrypoint",
  );
  assert(
    sceneRendererSource.includes("@mujoco/mujoco"),
    "mujocoWasmLoader.ts should import the official MuJoCo WASM bindings",
  );
}

testViteEntrypointIncludesMainTsxAndStlLoader();

console.log("vite entrypoint tests passed");
