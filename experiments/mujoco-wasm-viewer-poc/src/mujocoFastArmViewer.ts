import loadMujoco from "@mujoco/mujoco";
import mujocoWasmUrl from "@mujoco/mujoco/mujoco.wasm?url";
import {
  AmbientLight,
  BoxGeometry,
  BufferGeometry,
  Color,
  CylinderGeometry,
  DoubleSide,
  DirectionalLight,
  HemisphereLight,
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
import { matrixFromMujocoGeom } from "./mujocoSceneTransforms.js";
import { formatQpos, getCurrentFrame, loadQposFixtureFromUrl, stepNextFrameIndex, stepPreviousFrameIndex } from "./qposSync.js";
import type { QposFixture } from "./qposFrameTypes.js";

interface ViewerConfig {
  modelPath: string;
  fixturePath: string;
  mount: HTMLElement;
}

interface ShellElements {
  canvas: HTMLCanvasElement;
  status: HTMLPreElement;
  modelList: HTMLUListElement;
  playbackList: HTMLUListElement;
  statusBadge: HTMLDivElement;
  loadFixtureButton: HTMLButtonElement;
  playButton: HTMLButtonElement;
  pauseButton: HTMLButtonElement;
  stepNextButton: HTMLButtonElement;
  stepPreviousButton: HTMLButtonElement;
  resetButton: HTMLButtonElement;
}

const DEFAULT_WIDTH = 1280;
const DEFAULT_HEIGHT = 800;
const MAX_GEOMS = 2 ** 15;
const PLAYBACK_INTERVAL_MS = 180;
const SOURCE_HOME = "home keyframe";

const FAST_ARM_MESH_URLS = new Map<string, string>([
  ["BaseLink", "/assets/mujoco/fast_arm/meshes/BaseLink.stl"],
  ["SholderLink1", "/assets/mujoco/fast_arm/meshes/SholderLink1.stl"],
  ["SholderLink2", "/assets/mujoco/fast_arm/meshes/SholderLink2.stl"],
  ["UpperArmLink", "/assets/mujoco/fast_arm/meshes/UpperArmLink.stl"],
  ["ForeArmLink", "/assets/mujoco/fast_arm/meshes/ForeArmLink.stl"],
]);

function renderShell(mount: HTMLElement): ShellElements {
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
      .poc-controls { display: grid; gap: 10px; }
      .poc-control-row { display: flex; flex-wrap: wrap; gap: 8px; }
      .poc-button { appearance: none; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; border-radius: 10px; padding: 10px 12px; font: inherit; cursor: pointer; }
      .poc-button:hover:not(:disabled) { background: #111c33; }
      .poc-button:disabled { opacity: 0.45; cursor: not-allowed; }
      .poc-inline-note { color: #94a3b8; font-size: 12px; line-height: 1.45; }
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
          <ul id="model-list" class="poc-log"></ul>
        </section>
        <section class="poc-panel">
          <h2>Playback</h2>
          <div class="poc-controls">
            <div class="poc-control-row">
              <button id="load-fixture-button" class="poc-button">Load fixture</button>
              <button id="play-button" class="poc-button">Play</button>
              <button id="pause-button" class="poc-button">Pause</button>
              <button id="step-previous-button" class="poc-button">Step previous</button>
              <button id="step-next-button" class="poc-button">Step next</button>
              <button id="reset-button" class="poc-button">Reset to home</button>
            </div>
            <div class="poc-inline-note">Fixture: <code>/fixtures/fast_arm_sweep_x_qpos.json</code></div>
          </div>
          <ul id="playback-list" class="poc-log" style="margin-top: 12px;"></ul>
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
  const modelList = mount.querySelector<HTMLUListElement>("#model-list");
  const playbackList = mount.querySelector<HTMLUListElement>("#playback-list");
  const statusBadge = mount.querySelector<HTMLDivElement>("#status-badge");
  const loadFixtureButton = mount.querySelector<HTMLButtonElement>("#load-fixture-button");
  const playButton = mount.querySelector<HTMLButtonElement>("#play-button");
  const pauseButton = mount.querySelector<HTMLButtonElement>("#pause-button");
  const stepNextButton = mount.querySelector<HTMLButtonElement>("#step-next-button");
  const stepPreviousButton = mount.querySelector<HTMLButtonElement>("#step-previous-button");
  const resetButton = mount.querySelector<HTMLButtonElement>("#reset-button");

  if (
    canvas === null ||
    status === null ||
    modelList === null ||
    playbackList === null ||
    statusBadge === null ||
    loadFixtureButton === null ||
    playButton === null ||
    pauseButton === null ||
    stepNextButton === null ||
    stepPreviousButton === null ||
    resetButton === null
  ) {
    throw new Error("viewer shell failed to initialize");
  }

  return {
    canvas,
    status,
    modelList,
    playbackList,
    statusBadge,
    loadFixtureButton,
    playButton,
    pauseButton,
    stepNextButton,
    stepPreviousButton,
    resetButton,
  };
}

function setBadge(elements: ShellElements, text: string): void {
  elements.statusBadge.textContent = text;
}

function logLine(log: HTMLUListElement, label: string, value: string): void {
  const li = document.createElement("li");
  const strong = document.createElement("strong");
  strong.textContent = label;
  const span = document.createElement("span");
  span.textContent = value;
  li.append(strong, span);
  log.appendChild(li);
}

function renderKeyValueList(log: HTMLUListElement, entries: Array<[string, string]>): void {
  log.replaceChildren();
  entries.forEach(([label, value]) => {
    logLine(log, label, value);
  });
}

function formatMetadata(metadata: Record<string, unknown>): string {
  return JSON.stringify(metadata, null, 2);
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
  scene.add(new HemisphereLight(0xbfd7ff, 0x1e293b, 0.8));

  const keyLight = new DirectionalLight(0xffffff, 1.8);
  keyLight.position.set(2.5, -2.5, 4.0);
  scene.add(keyLight);

  const fillLight = new DirectionalLight(0xdbeafe, 0.6);
  fillLight.position.set(-2.0, 1.5, 2.0);
  scene.add(fillLight);

  const meshGeometryCache = new Map<string, BufferGeometry>();
  const objectByGeomIndex = new Map<number, Mesh>();
  const stlLoader = new STLLoader();

  let mujocoApi: any;
  let model: any;
  let data: any;
  let mjvScene: any;
  let mjvOption: any;
  let mjvPerturb: any;
  let mjvCamera: any;
  let defaultQpos: number[] = [];
  let homeQpos: number[] = [];
  let loadedFixture: QposFixture | null = null;
  let activeSource: "home" | "fixture" = "home";
  let selectedFixtureFrameIndex = 0;
  let playbackStatus: "loading" | "ready" | "playing" | "paused" | "error" = "loading";
  let playbackTimer: number | null = null;
  let hasInitializedModel = false;

  async function loadStl(url: string): Promise<BufferGeometry> {
    const cached = meshGeometryCache.get(url);
    if (cached !== undefined) {
      return cached;
    }

    const geometry = await stlLoader.loadAsync(url);
    meshGeometryCache.set(url, geometry);
    return geometry;
  }

  async function syncSceneFromCurrentData(): Promise<void> {
    mujocoApi.mjv_updateScene(
      model,
      data,
      mjvOption,
      mjvPerturb,
      mjvCamera,
      mujocoApi.mjtCatBit.mjCAT_ALL.value,
      mjvScene,
    );

    const meshNameById = new Map<number, string>();
    for (let meshIndex = 0; meshIndex < model.nmesh; meshIndex += 1) {
      const meshName = mujocoApi.mj_id2name(model, mujocoApi.mjtObj.mjOBJ_MESH.value, meshIndex);
      if (meshName !== null) {
        meshNameById.set(meshIndex, meshName);
      }
    }

    const missingMeshReferences: string[] = [];
    const geoms = mjvScene.geoms;
    for (let geomIndex = 0; geomIndex < geoms.size(); geomIndex += 1) {
      const geom = geoms.get(geomIndex);
      const key = geomIndex;
      let mesh = objectByGeomIndex.get(key);
      if (mesh === undefined) {
        let geometry: BufferGeometry;
        if (geom.type === mujocoApi.mjtGeom.mjGEOM_MESH.value) {
          const sourceGeom = geom.objtype === mujocoApi.mjtObj.mjOBJ_GEOM.value ? model.geom(geom.objid) : null;
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
      mesh.matrix.copy(matrixFromMujocoGeom(geom));
      mesh.matrixWorldNeedsUpdate = true;
      geom.delete();
    }
    geoms.delete();

    if (missingMeshReferences.length > 0) {
      const summary = missingMeshReferences.join(", ");
      shell.status.textContent += `\nmissing mesh refs: ${summary}`;
    }
  }

  function getCurrentFixtureFrame(): { frameIndex: number; frame: QposFixture["frames"][number] } | null {
    if (loadedFixture === null) {
      return null;
    }

    return {
      frameIndex: selectedFixtureFrameIndex,
      frame: getCurrentFrame(loadedFixture, selectedFixtureFrameIndex),
    };
  }

  function updateStaticModelInfo(): void {
    const keyNames: string[] = [];
    let homeKeyIndex: number | null = null;
    for (let keyIndex = 0; keyIndex < model.nkey; keyIndex += 1) {
      const keyName = mujocoApi.mj_id2name(model, mujocoApi.mjtObj.mjOBJ_KEY.value, keyIndex);
      if (keyName !== null) {
        keyNames.push(keyName);
      }
      if (keyName === "home") {
        homeKeyIndex = keyIndex;
      }
    }

    renderKeyValueList(shell.modelList, [
      ["nq", String(model.nq)],
      ["nv", String(model.nv)],
      ["nbody", String(model.nbody)],
      ["ngeom", String(model.ngeom)],
      ["nmesh", String(model.nmesh)],
      ["nkey", String(model.nkey)],
      ["keyframes", keyNames.join(", ") || "(none)"],
      ["default qpos", formatQpos(defaultQpos)],
      ["home keyframe", homeKeyIndex === null ? "(missing)" : formatQpos(homeQpos)],
    ]);
  }

  function updatePlaybackSummary(): void {
    const fixtureFrame = getCurrentFixtureFrame();
    const currentFrameLabel = activeSource === "fixture" && fixtureFrame !== null ? String(fixtureFrame.frame.frame_index) : SOURCE_HOME;
    const currentT = activeSource === "fixture" && fixtureFrame !== null ? fixtureFrame.frame.t_s.toString() : SOURCE_HOME;
    const currentQpos =
      activeSource === "fixture" && fixtureFrame !== null ? formatQpos(fixtureFrame.frame.qpos) : formatQpos(homeQpos);
    const currentMetadata =
      activeSource === "fixture" && fixtureFrame !== null
        ? formatMetadata(fixtureFrame.frame.metadata)
        : formatMetadata({ source: SOURCE_HOME });

    renderKeyValueList(shell.playbackList, [
      ["status", playbackStatus],
      ["source label", activeSource === "fixture" ? "python-native-mujoco fixture" : SOURCE_HOME],
      ["current frame index", currentFrameLabel],
      ["current t_s", currentT],
      ["current qpos", currentQpos],
      ["current metadata", currentMetadata],
      ["fixture path", loadedFixture === null ? "(not loaded)" : loadedFixture.model_path],
      ["fixture preset", loadedFixture === null ? "(not loaded)" : loadedFixture.preset],
      ["fixture qpos length", loadedFixture === null ? "(not loaded)" : String(loadedFixture.qpos_length)],
      ["model nq", String(model.nq)],
      [
        "qpos_length match",
        loadedFixture === null ? "(not loaded)" : String(loadedFixture.qpos_length === model.nq),
      ],
      ["selected fixture cursor", loadedFixture === null ? "(not loaded)" : String(selectedFixtureFrameIndex)],
    ]);

    shell.status.textContent = [
      `model path: ${config.modelPath}`,
      `fixture path: ${config.fixturePath}`,
      `status: ${playbackStatus}`,
      `source label: ${activeSource === "fixture" ? "python-native-mujoco fixture" : SOURCE_HOME}`,
      `current frame index: ${currentFrameLabel}`,
      `current t_s: ${currentT}`,
      `current qpos: ${currentQpos}`,
      `current metadata: ${currentMetadata}`,
      `fixture loaded: ${loadedFixture === null ? "no" : "yes"}`,
      `browser-side qpos recompute: disabled`,
    ].join("\n");

    setBadge(shell, playbackStatus);
    shell.playButton.disabled = loadedFixture === null || playbackStatus === "loading";
    shell.pauseButton.disabled = loadedFixture === null || playbackStatus === "loading";
    shell.stepNextButton.disabled = loadedFixture === null || playbackStatus === "loading";
    shell.stepPreviousButton.disabled = loadedFixture === null || playbackStatus === "loading";
    shell.resetButton.disabled = playbackStatus === "loading";
    shell.loadFixtureButton.disabled = playbackStatus === "loading";
  }

  function applyHomePose(): void {
    activeSource = "home";
    data.qpos.set(homeQpos);
    mujocoApi.mj_forward(model, data);
  }

  function applyFixtureFrame(frameIndex: number): void {
    if (loadedFixture === null) {
      throw new Error("fixture is not loaded");
    }

    const frame = getCurrentFrame(loadedFixture, frameIndex);
    selectedFixtureFrameIndex = frameIndex;
    activeSource = "fixture";
    data.qpos.set(frame.qpos);
    mujocoApi.mj_forward(model, data);
  }

  async function renderCurrentPose(): Promise<void> {
    await syncSceneFromCurrentData();
    updatePlaybackSummary();
  }

  async function showHomePose(): Promise<void> {
    applyHomePose();
    await renderCurrentPose();
  }

  async function showFixtureFrame(frameIndex: number): Promise<void> {
    applyFixtureFrame(frameIndex);
    await renderCurrentPose();
  }

  function stopPlaybackTimer(): void {
    if (playbackTimer !== null) {
      window.clearInterval(playbackTimer);
      playbackTimer = null;
    }
  }

  async function startPlaybackTimer(): Promise<void> {
    if (playbackTimer !== null || loadedFixture === null) {
      return;
    }

    if (activeSource === "home") {
      await showFixtureFrame(selectedFixtureFrameIndex);
    }

    playbackStatus = "playing";
    updatePlaybackSummary();
    playbackTimer = window.setInterval(() => {
      void advancePlaybackStep();
    }, PLAYBACK_INTERVAL_MS);
  }

  async function advancePlaybackStep(): Promise<void> {
    if (loadedFixture === null) {
      return;
    }

    if (activeSource === "home") {
      activeSource = "fixture";
    }

    const nextFrameIndex = stepNextFrameIndex(selectedFixtureFrameIndex, loadedFixture.frames.length);
    await showFixtureFrame(nextFrameIndex);

    if (selectedFixtureFrameIndex >= loadedFixture.frames.length - 1) {
      stopPlaybackTimer();
      playbackStatus = "paused";
      updatePlaybackSummary();
    }
  }

  async function stepToPreviousFrame(): Promise<void> {
    if (loadedFixture === null) {
      return;
    }

    stopPlaybackTimer();
    playbackStatus = "paused";
    const previousFrameIndex = stepPreviousFrameIndex(selectedFixtureFrameIndex);
    await showFixtureFrame(previousFrameIndex);
  }

  async function stepToNextFrame(): Promise<void> {
    if (loadedFixture === null) {
      return;
    }

    stopPlaybackTimer();
    playbackStatus = "paused";
    const nextFrameIndex = stepNextFrameIndex(selectedFixtureFrameIndex, loadedFixture.frames.length);
    await showFixtureFrame(nextFrameIndex);
  }

  async function loadFixture(): Promise<void> {
    playbackStatus = "loading";
    updatePlaybackSummary();

    try {
      loadedFixture = await loadQposFixtureFromUrl(config.fixturePath, model.nq);
      selectedFixtureFrameIndex = 0;
      stopPlaybackTimer();
      playbackStatus = "paused";
      await showFixtureFrame(selectedFixtureFrameIndex);
    } catch (error) {
      stopPlaybackTimer();
      loadedFixture = null;
      activeSource = "home";
      const message = error instanceof Error ? error.message : String(error);
      playbackStatus = "error";
      shell.status.textContent = message;
      shell.playbackList.innerHTML = "";
      renderKeyValueList(shell.playbackList, [["error", message]]);
      setBadge(shell, "error");
      shell.loadFixtureButton.disabled = false;
      shell.playButton.disabled = true;
      shell.pauseButton.disabled = true;
      shell.stepNextButton.disabled = true;
      shell.stepPreviousButton.disabled = true;
      shell.resetButton.disabled = false;
      console.error(error);
      return;
    }
  }

  async function initializeModel(): Promise<void> {
    setBadge(shell, "loading");

    mujocoApi = (await loadMujoco({
      locateFile: (file: string) => (file === "mujoco.wasm" ? mujocoWasmUrl : file),
    })) as any;

    const xml = await fetch(config.modelPath).then(async (response) => {
      if (!response.ok) {
        throw new Error(`failed to fetch ${config.modelPath}: ${response.status} ${response.statusText}`);
      }
      return response.text();
    });
    const vfs = new mujocoApi.MjVFS();
    try {
      const armResponse = await fetch("/assets/mujoco/fast_arm/arm.xml");
      if (!armResponse.ok) {
        throw new Error(`failed to fetch /assets/mujoco/fast_arm/arm.xml: ${armResponse.status} ${armResponse.statusText}`);
      }
      vfs.addBuffer("arm.xml", new Uint8Array(await armResponse.arrayBuffer()));
      for (const [meshName, meshUrl] of FAST_ARM_MESH_URLS.entries()) {
        const meshResponse = await fetch(meshUrl);
        if (!meshResponse.ok) {
          throw new Error(`failed to fetch ${meshUrl}: ${meshResponse.status} ${meshResponse.statusText}`);
        }
        vfs.addBuffer(`meshes/${meshName}.stl`, new Uint8Array(await meshResponse.arrayBuffer()));
      }

      model = mujocoApi.MjModel.from_xml_string(xml, vfs);
      data = new mujocoApi.MjData(model);
      const modelStat = model.stat as any;
      const modelCenter = Array.from(modelStat.center as ArrayLike<number>);
      const modelExtent = Number(modelStat.extent);
      controls.target.set(modelCenter[0], modelCenter[1], modelCenter[2]);
      camera.position.set(
        modelCenter[0] + modelExtent * 1.8,
        modelCenter[1] - modelExtent * 1.9,
        modelCenter[2] + modelExtent * 1.3,
      );
      controls.update();

      defaultQpos = Array.from(data.qpos);
      const homeKey = model.key("home");
      if (homeKey !== null) {
        homeQpos = Array.from(homeKey.qpos);
        data.qpos.set(homeQpos);
      } else {
        homeQpos = [...defaultQpos];
      }
      mujocoApi.mj_forward(model, data);
      mjvScene = new mujocoApi.MjvScene(model, MAX_GEOMS);
      mjvOption = new mujocoApi.MjvOption();
      mjvPerturb = new mujocoApi.MjvPerturb();
      mjvCamera = new mujocoApi.MjvCamera();

      updateStaticModelInfo();
      await syncSceneFromCurrentData();
      playbackStatus = "ready";
      hasInitializedModel = true;
      updatePlaybackSummary();
      setBadge(shell, "ready");
      shell.loadFixtureButton.disabled = false;
      shell.resetButton.disabled = false;
    } finally {
      vfs.delete();
    }
  }

  async function start(): Promise<void> {
    try {
      shell.loadFixtureButton.disabled = true;
      shell.playButton.disabled = true;
      shell.pauseButton.disabled = true;
      shell.stepNextButton.disabled = true;
      shell.stepPreviousButton.disabled = true;
      shell.resetButton.disabled = true;
      await initializeModel();
      if (!hasInitializedModel) {
        throw new Error("model initialization did not complete");
      }

      shell.loadFixtureButton.addEventListener("click", () => {
        void loadFixture();
      });
      shell.playButton.addEventListener("click", () => {
        void startPlaybackTimer();
      });
      shell.pauseButton.addEventListener("click", () => {
        stopPlaybackTimer();
        playbackStatus = "paused";
        updatePlaybackSummary();
      });
      shell.stepNextButton.addEventListener("click", () => {
        void stepToNextFrame();
      });
      shell.stepPreviousButton.addEventListener("click", () => {
        void stepToPreviousFrame();
      });
      shell.resetButton.addEventListener("click", () => {
        stopPlaybackTimer();
        playbackStatus = loadedFixture === null ? "ready" : "paused";
        void showHomePose();
      });

      await showHomePose();

      const animate = (): void => {
        controls.update();
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setBadge(shell, "error");
      playbackStatus = "error";
      shell.status.textContent = message;
      shell.modelList.innerHTML = "";
      shell.playbackList.innerHTML = "";
      renderKeyValueList(shell.playbackList, [["error", message]]);
      console.error(error);
    }
  }

  return { start };
}
