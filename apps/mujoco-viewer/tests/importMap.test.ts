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
  const sourcePath = resolve(process.cwd(), "src", "viewer", "fastArmMeshes.ts");
  return readFileSync(sourcePath, "utf-8");
}

function extractImportMap(html: string): Record<string, string> {
  const match = html.match(/<script type="importmap">\s*([\s\S]*?)\s*<\/script>/i);
  assert(match !== null, "index.html should contain an import map");

  const jsonText = match[1].trim();
  const parsed = JSON.parse(jsonText) as {
    imports?: Record<string, string>;
  };

  return parsed.imports ?? {};
}

function testImportMapIncludesThreeAndStlLoader(): void {
  const html = readIndexHtml();
  const imports = extractImportMap(html);
  const fastArmMeshSource = readFastArmMeshSource();

  assert(imports.three === "./node_modules/three/build/three.module.js", "index.html should map three");
  assert(
    imports["three/examples/jsm/"] === "./node_modules/three/examples/jsm/",
    "index.html should map the three examples jsm prefix",
  );
  assert(
    "three/examples/jsm/loaders/STLLoader.js" in imports || "three/examples/jsm/" in imports,
    "index.html should make STLLoader resolvable in the browser entry",
  );
  assert(
    fastArmMeshSource.includes('from "three/examples/jsm/loaders/STLLoader.js"'),
    "fastArmMeshes.ts should import STLLoader from three examples jsm",
  );
  assert(
    "three/examples/jsm/" in imports,
    "index.html should provide the prefix mapping required by STLLoader",
  );
}

testImportMapIncludesThreeAndStlLoader();

console.log("import map tests passed");
