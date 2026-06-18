import loadMujoco from "@mujoco/mujoco";
import mujocoWasmUrl from "@mujoco/mujoco/mujoco.wasm?url";
import {
  AmbientLight,
  BoxGeometry,
  BufferGeometry,
  Color,
  CylinderGeometry,
  DoubleSide,
  Mesh,
  MeshPhongMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

interface ViewerConfig {
  modelPath: string;
  mount: HTMLElement;
}

const DEFAULT_WIDTH = 1280;
const DEFAULT_HEIGHT = 800;
const MAX_GEOMS = 2 ** 15;

const FAST_ARM_MESH_URLS = new Map<string, string>([
  ["BaseLink", "/assets/mujoco/fast_arm/meshes/BaseLink.stl"],
  ["SholderLink1", "/assets/mujoco/fast_arm/meshes/SholderLink1.stl"],
  ["SholderLink2", "/assets/mujoco/fast_arm/meshes/SholderLink2.stl"],
  ["UpperArmLink", "/assets/mujoco/fast_arm/meshes/UpperArmLink.stl"],
  ["ForeArmLink", "/assets/mujoco/fast_arm/meshes/ForeArmLink.stl"],
]);

function renderShell(mount: HTMLElement): { canvas: HTMLCanvasElement; status: HTMLPreElement; log: HTMLUListElement } {
  mount.innerHTML = `
    <style>
      html, body { margin: 0; background: #08111f; color: #e2e8f0; font-family: ui-sans-serif, system-ui, sans-serif; }
      .poc-shell { display: grid; gap: 16px; padding: 16px; }
      .poc-header { display: flex; justify-content: space-between; align-items: start; gap: 16px; }
      .poc-kicker { text-transform: uppercase; letter-spacing: 0.16em; font-size: 12px; color: #38bdf8; }
      .poc-header h1 { margin: 4px 0 6px; font-size: 28px; }
      .poc-header p { margin: 0; color: #94a3b8; }
      .poc-badge { padding: 10px 14px; border-radius: 999px; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; }
      .poc-grid { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 16px; align-items: start; }
      .poc-panel { background: rgba(15, 23, 42, 0.96); border: 1px solid rgba(51, 65, 85, 0.9); border-radius: 16px; padding: 16px; box-shadow: 0 24px 60px rgba(2, 6, 23, 0.35); }
      .poc-panel h2 { margin: 0 0 12px; font-size: 16px; color: #f8fafc; }
      .poc-canvas-panel { min-height: 760px; }
      #viewer-canvas { width: 100%; height: 760px; display: block; border-radius: 12px; background: radial-gradient(circle at top, #10213f, #050816 70%); }
      .poc-log { margin: 0; padding-left: 18px; display: grid; gap: 8px; }
      .poc-log li { display: flex; justify-content: space-between; gap: 12px; }
      .poc-log strong { color: #f8fafc; font-weight: 600; }
      .poc-log span { color: #cbd5e1; text-align: right; word-break: break-word; }
      .poc-status { margin: 0; white-space: pre-wrap; color: #cbd5e1; }
      @media (max-width: 1000px) {
        .poc-grid { grid-template-columns: 1fr; }
        .poc-canvas-panel, #viewer-canvas { height: 60vh; min-height: 480px; }
      }
    </style>
    <section class="poc-shell">
      <header class="poc-header">
        <div>
          <div class="poc-kicker">official @mujoco/mujoco PoC</div>
          <h1>MuJoCo WASM fast_arm viewer</h1>
          <p>Repository assets are loaded directly from <code>/assets/mujoco/fast_arm</code>.</p>
        </div>
        <div id="status-badge" class="poc-badge">booting</div>
      </header>
      <div class="poc-grid">
        <section class="poc-panel">
          <h2>Model Info</h2>
          <ul id="log-list" class="poc-log"></ul>
        </section>
        <section class="poc-panel poc-canvas-panel">
          <canvas id="viewer-canvas"></canvas>
        </section>
      </div>
      <section class="poc-panel">
        <h2>Notes</h2>
        <pre id="status-text" class="poc-status">starting...</pre>
      </section>
    </section>
  `;

  const canvas = mount.querySelector<HTMLCanvasElement>("#viewer-canvas");
  const status = mount.querySelector<HTMLPreElement>("#status-text");
  const log = mount.querySelector<HTMLUListElement>("#log-list");
  if (canvas === null || status === null || log === null) {
    throw new Error("viewer shell failed to initialize");
  }
  return { canvas, status, log };
}

function setBadge(mount: HTMLElement, text: string): void {
  const badge = mount.querySelector<HTMLElement>("#status-badge");
  if (badge !== null) {
    badge.textContent = text;
  }
}

function logLine(log: HTMLUListElement, label: string, value: string): void {
  const li = document.createElement("li");
  li.innerHTML = `<strong>${label}</strong><span>${value}</span>`;
  log.appendChild(li);
}

function formatArray(values: any): string {
  return `[${Array.from(values as ArrayLike<unknown>, (value) => Number(value).toString()).join(", ")}]`;
}

async function fetchText(path: string): Promise<string> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`failed to fetch ${path}: ${response.status} ${response.statusText}`);
  }
  return response.text();
}

async function fetchBytes(path: string): Promise<Uint8Array> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`failed to fetch ${path}: ${response.status} ${response.statusText}`);
  }
  return new Uint8Array(await response.arrayBuffer());
}

function buildPrimitiveGeometry(type: number, size: ArrayLike<number>): BufferGeometry {
  if (type === 0) {
    return new PlaneGeometry(20, 20);
  }
  if (type === 2) {
    return new SphereGeometry(Number(size[0] ?? 1));
  }
  if (type === 3) {
    const radius = Number(size[0] ?? 1);
    const length = 2 * Number(size[2] ?? 1);
    const geom = new CylinderGeometry(radius, radius, length, 32);
    geom.rotateX(Math.PI / 2);
    return geom;
  }
  if (type === 4) {
    const geom = new SphereGeometry(1);
    geom.scale(Number(size[0] ?? 1), Number(size[1] ?? 1), Number(size[2] ?? 1));
    return geom;
  }
  if (type === 5) {
    const radiusTop = Number(size[0] ?? 1);
    const radiusBottom = Number(size[1] ?? 1);
    const length = 2 * Number(size[2] ?? 1);
    const geom = new CylinderGeometry(radiusTop, radiusBottom, length, 32);
    geom.rotateX(Math.PI / 2);
    return geom;
  }
  if (type === 6) {
    return new BoxGeometry(2 * Number(size[0] ?? 1), 2 * Number(size[1] ?? 1), 2 * Number(size[2] ?? 1));
  }
  return new BufferGeometry();
}

function matrixFromGeom(geom: any): [number, number, number, number, number, number, number, number, number, number, number, number, number, number, number, number] {
  return [
    geom.mat[0], geom.mat[1], geom.mat[2], geom.pos[0],
    geom.mat[3], geom.mat[4], geom.mat[5], geom.pos[1],
    geom.mat[6], geom.mat[7], geom.mat[8], geom.pos[2],
    0, 0, 0, 1,
  ];
}

export function createMujocoFastArmViewer(config: ViewerConfig) {
  const shell = renderShell(config.mount);
  const scene = new Scene();
  scene.background = new Color("#08111f");

  const renderer = new WebGLRenderer({ canvas: shell.canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT, false);
  renderer.outputColorSpace = SRGBColorSpace;

  const camera = new PerspectiveCamera(45, DEFAULT_WIDTH / DEFAULT_HEIGHT, 0.01, 100);
  camera.position.set(1.8, -1.8, 1.5);
  camera.up.set(0, 0, 1);

  const controls = new OrbitControls(camera, shell.canvas);
  controls.target.set(0.15, 0, 0.2);
  controls.update();

  scene.add(new AmbientLight(0xffffff, 1.0));

  const meshGeometryCache = new Map<string, BufferGeometry>();
  const objectByGeomIndex = new Map<number, Mesh>();
  const stlLoader = new STLLoader();

  async function loadStl(url: string): Promise<BufferGeometry> {
    const cached = meshGeometryCache.get(url);
    if (cached !== undefined) {
      return cached;
    }
    const geometry = await stlLoader.loadAsync(url);
    meshGeometryCache.set(url, geometry);
    return geometry;
  }

  async function start(): Promise<void> {
    setBadge(config.mount, "loading");
    try {
      const mujoco = (await loadMujoco({
        locateFile: (file: string) => (file === "mujoco.wasm" ? mujocoWasmUrl : file),
      })) as any;
      const xml = await fetchText(config.modelPath);
      const vfs = new mujoco.MjVFS();
      try {
        vfs.addBuffer("arm.xml", await fetchBytes("/assets/mujoco/fast_arm/arm.xml"));
        for (const [meshName, meshUrl] of FAST_ARM_MESH_URLS.entries()) {
          vfs.addBuffer(`meshes/${meshName}.stl`, await fetchBytes(meshUrl));
        }

        const model = mujoco.MjModel.from_xml_string(xml, vfs);
        const data = new mujoco.MjData(model);

        const keyNames: string[] = [];
        let homeKeyIndex: number | null = null;
        for (let keyIndex = 0; keyIndex < model.nkey; keyIndex += 1) {
          const keyName = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_KEY.value, keyIndex);
          if (keyName !== null) {
            keyNames.push(keyName);
          }
          if (keyName === "home") {
            homeKeyIndex = keyIndex;
          }
        }

        const qpos0 = Array.from(data.qpos);
        const homeKey = model.key("home");
        const homeQpos = Array.from(homeKey.qpos);
        if (homeKeyIndex !== null) {
          data.qpos.set(homeQpos);
        }
        mujoco.mj_forward(model, data);

        const mjvScene = new mujoco.MjvScene(model, MAX_GEOMS);
        const mjvOption = new mujoco.MjvOption();
        const mjvPerturb = new mujoco.MjvPerturb();
        const mjvCamera = new mujoco.MjvCamera();

        logLine(shell.log, "nq", String(model.nq));
        logLine(shell.log, "nv", String(model.nv));
        logLine(shell.log, "nbody", String(model.nbody));
        logLine(shell.log, "ngeom", String(model.ngeom));
        logLine(shell.log, "nmesh", String(model.nmesh));
        logLine(shell.log, "nkey", String(model.nkey));
        logLine(shell.log, "keyframes", keyNames.join(", ") || "(none)");
        logLine(shell.log, "default qpos", formatArray(qpos0));
        logLine(shell.log, "home qpos", formatArray(homeQpos));

        shell.status.textContent = [
          `model path: ${config.modelPath}`,
          `xml loaded: yes`,
          `home keyframe applied: ${homeKeyIndex !== null ? "yes" : "no"}`,
          `home keyframe qpos: ${formatArray(homeQpos)}`,
          `qpos0: ${formatArray(qpos0)}`,
          `qpos after home: ${formatArray(data.qpos)}`,
          `keyframes: ${keyNames.join(", ") || "(none)"}`,
        ].join("\n");

        mujoco.mjv_updateScene(
          model,
          data,
          mjvOption,
          mjvPerturb,
          mjvCamera,
          mujoco.mjtCatBit.mjCAT_ALL.value,
          mjvScene,
        );

        const meshNameById = new Map<number, string>();
        for (let meshIndex = 0; meshIndex < model.nmesh; meshIndex += 1) {
          const meshName = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_MESH.value, meshIndex);
          if (meshName !== null) {
            meshNameById.set(meshIndex, meshName);
          }
        }
        logLine(
          shell.log,
          "model meshes",
          Array.from(meshNameById.entries(), ([meshIndex, meshName]) => `${meshIndex}:${meshName}`).join(", ") ||
            "(none)",
        );

        const missingMeshReferences: string[] = [];
        const geoms = mjvScene.geoms;
        for (let geomIndex = 0; geomIndex < geoms.size(); geomIndex += 1) {
          const geom = geoms.get(geomIndex);
          const key = geomIndex;
          let mesh = objectByGeomIndex.get(key);
          if (mesh === undefined) {
            let geometry: BufferGeometry;
            if (geom.type === mujoco.mjtGeom.mjGEOM_MESH.value) {
              const sourceGeom = geom.objtype === mujoco.mjtObj.mjOBJ_GEOM.value ? model.geom(geom.objid) : null;
              const meshId = sourceGeom === null ? geom.dataid : sourceGeom.dataid;
              const meshName = meshNameById.get(meshId);
              const meshUrl = meshName === undefined ? null : FAST_ARM_MESH_URLS.get(meshName);
              if (meshUrl === undefined || meshUrl === null) {
                const sourceGeomName = sourceGeom === null ? null : sourceGeom.name;
                missingMeshReferences.push(
                  `${geomIndex}:${geom.dataid}${meshName === undefined ? "" : `(${meshName})`}` +
                    `${sourceGeomName === null ? "" : `[${sourceGeomName}]`}`,
                );
                geometry = buildPrimitiveGeometry(6, geom.size);
              } else {
                geometry = await loadStl(meshUrl);
              }
            } else {
              geometry = buildPrimitiveGeometry(geom.type, geom.size);
            }

            const material = new MeshPhongMaterial({
              color: new Color(geom.rgba[0], geom.rgba[1], geom.rgba[2]),
              transparent: geom.rgba[3] < 1,
              opacity: geom.rgba[3],
              side: DoubleSide,
            });

            mesh = new Mesh(geometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            objectByGeomIndex.set(key, mesh);
            scene.add(mesh);
          }

          mesh.matrixAutoUpdate = false;
          mesh.matrix.fromArray(matrixFromGeom(geom));
          mesh.matrixWorldNeedsUpdate = true;
          geom.delete();
        }
        geoms.delete();
        mjvScene.delete();

        if (missingMeshReferences.length > 0) {
          const summary = missingMeshReferences.join(", ");
          logLine(shell.log, "missing mesh refs", summary);
          shell.status.textContent += `\nmissing mesh refs: ${summary}`;
        }

        setBadge(config.mount, "ready");

        const animate = (): void => {
          controls.update();
          renderer.render(scene, camera);
          requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
      } finally {
        vfs.delete();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setBadge(config.mount, "failed");
      shell.status.textContent = message;
      shell.log.innerHTML = "";
      logLine(shell.log, "error", message);
      console.error(error);
    }
  }

  return { start };
}
