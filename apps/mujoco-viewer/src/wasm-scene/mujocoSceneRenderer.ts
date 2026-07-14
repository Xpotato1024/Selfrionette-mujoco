import {
  AmbientLight,
  AxesHelper,
  BoxGeometry,
  BufferGeometry,
  Color,
  CylinderGeometry,
  DoubleSide,
  DirectionalLight,
  Float32BufferAttribute,
  HemisphereLight,
  CanvasTexture,
  Mesh,
  MeshPhongMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  SphereGeometry,
  SRGBColorSpace,
  NearestFilter,
  RepeatWrapping,
  Uint32BufferAttribute,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { TransportPayloadV0 } from "../types/transportPayload.js";
import type { ViewerRobotProfile } from "../robot-profiles/types.js";
import { createViewerWebSocketClient, type ViewerWebSocketClient } from "../transport/websocketClient.js";
import { loadMujocoWasm } from "./mujocoWasmLoader.js";
import { matrixFromMujocoGeom } from "./mujocoSceneTransforms.js";
import {
  formatQpos,
  resolveNamedInitialKeyframe,
  resolveTransportQpos,
} from "./mujocoQposSync.js";
import { resolveBodyVisualStyle } from "./visualStyles.js";
import type { BodyVisualStyle } from "./visualStyles.js";
import {
  createInitialProductViewerState,
  buildProductViewerInputOverlayState,
  formatViewerStatusText,
  type ProductViewerState,
} from "./productViewerState.js";
import {
  createViewerFrameTiming,
  type ViewerPayloadCandidate,
} from "./viewerFrameTiming.js";

export interface MujocoSceneRendererOptions {
  canvas: HTMLCanvasElement;
  profile: ViewerRobotProfile;
  websocketUrl?: string | null;
  onStateChange: (state: ProductViewerState) => void;
  onError?: (error: Error) => void;
}

export interface MujocoSceneRenderer {
  start(): Promise<void>;
  dispose(): void;
}

const DEFAULT_WIDTH = 1280;
const DEFAULT_HEIGHT = 800;
const MAX_GEOMS = 2 ** 15;
function createCheckerFloorTexture(): CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const context = canvas.getContext("2d");
  if (context === null) {
    return new CanvasTexture(canvas);
  }

  const tiles = 4;
  const tileSize = canvas.width / tiles;
  context.fillStyle = "#f8fafc";
  context.fillRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < tiles; y += 1) {
    for (let x = 0; x < tiles; x += 1) {
      if ((x + y) % 2 === 0) {
        context.fillStyle = "#0f172a";
      } else {
        context.fillStyle = "#f8fafc";
      }
      context.fillRect(x * tileSize, y * tileSize, tileSize, tileSize);
    }
  }

  const texture = new CanvasTexture(canvas);
  texture.wrapS = RepeatWrapping;
  texture.wrapT = RepeatWrapping;
  texture.repeat.set(4.0, 4.0);
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
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

function createStatePatch(
  previous: ProductViewerState,
  patch: Partial<ProductViewerState> & { statusText?: string },
): ProductViewerState {
  const next = {
    ...previous,
    ...patch,
  };
  next.statusText = patch.statusText ?? formatViewerStatusText(next);
  next.currentQposText = patch.currentQposText ?? (next.currentQpos === null ? "[]" : formatQpos(next.currentQpos));
  return next;
}

export function createMujocoSceneRenderer(options: MujocoSceneRendererOptions): MujocoSceneRenderer {
  const frameTiming = createViewerFrameTiming();
  const state = createInitialProductViewerState(options.profile);
  const emitState = (patch: Partial<ProductViewerState> & { statusText?: string }): void => {
    frameTiming.recordUiStateUpdate();
    Object.assign(state, createStatePatch(state, { ...patch, viewerTiming: frameTiming.snapshot() }));
    options.onStateChange({ ...state });
  };

  const scene = new Scene();
  scene.background = new Color("#08111f");

  const renderer = new WebGLRenderer({ canvas: options.canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(DEFAULT_WIDTH, DEFAULT_HEIGHT, false);
  renderer.outputColorSpace = SRGBColorSpace;

  const camera = new PerspectiveCamera(45, DEFAULT_WIDTH / DEFAULT_HEIGHT, 0.01, 100);
  camera.position.set(1.8, -1.8, 1.5);
  camera.up.set(0, 0, 1);

  const controls = new OrbitControls(camera, options.canvas);
  controls.target.set(0.15, 0, 0.2);
  controls.update();

  scene.add(new AmbientLight(0xffffff, 1.0));
  scene.add(new HemisphereLight(0xbfd7ff, 0x1e293b, 0.8));
  const axesHelper = new AxesHelper(0.5);
  axesHelper.position.set(0, 0, 0);
  scene.add(axesHelper);

  const keyLight = new DirectionalLight(0xffffff, 1.8);
  keyLight.position.set(2.5, -2.5, 4.0);
  scene.add(keyLight);

  const fillLight = new DirectionalLight(0xdbeafe, 0.6);
  fillLight.position.set(-2.0, 1.5, 2.0);
  scene.add(fillLight);

  const meshGeometryCache = new Map<number, BufferGeometry>();
  const objectByGeomIndex = new Map<number, Mesh>();
  const materialByKey = new Map<string, MeshPhongMaterial>();
  const floorTexture = createCheckerFloorTexture();
  const floorMaterial = new MeshPhongMaterial({
    color: new Color("#d4d4d8"),
    map: floorTexture,
    transparent: false,
    opacity: 1,
    side: DoubleSide,
    shininess: 0,
    specular: new Color("#111827"),
  });
  const modelMeshNameById = new Map<number, string>();

  let mujocoApi: any;
  let model: any;
  let data: any;
  let mjvScene: any;
  let mjvOption: any;
  let mjvPerturb: any;
  let mjvCamera: any;
  let websocketClient: ViewerWebSocketClient | null = null;
  let startupQpos: number[] = [];
  let hasLoaded = false;
  let disposed = false;
  let frameHandle: number | null = null;

  const websocketUrl =
    options.websocketUrl === undefined || options.websocketUrl === null || options.websocketUrl.trim() === ""
      ? null
      : options.websocketUrl;

  const updateStatus = (patch: Partial<ProductViewerState> & { statusText?: string }): void => {
    emitState(patch);
  };

  const buildCompiledMeshGeometry = (meshId: number): BufferGeometry => {
    const cached = meshGeometryCache.get(meshId);
    if (cached !== undefined) {
      return cached;
    }

    const vertexStart = model.mesh_vertadr[meshId];
    const vertexCount = model.mesh_vertnum[meshId];
    const faceStart = model.mesh_faceadr[meshId];
    const faceCount = model.mesh_facenum[meshId];
    if (vertexStart === undefined || vertexCount === undefined || faceStart === undefined || faceCount === undefined) {
      throw new Error(`missing compiled mesh data for mesh ${meshId}`);
    }

    const positionAttribute = new Float32Array(vertexCount * 3);
    for (let vertexIndex = 0; vertexIndex < vertexCount; vertexIndex += 1) {
      const sourceIndex = (vertexStart + vertexIndex) * 3;
      const targetIndex = vertexIndex * 3;
      positionAttribute[targetIndex] = Number(model.mesh_vert[sourceIndex] ?? 0);
      positionAttribute[targetIndex + 1] = Number(model.mesh_vert[sourceIndex + 1] ?? 0);
      positionAttribute[targetIndex + 2] = Number(model.mesh_vert[sourceIndex + 2] ?? 0);
    }

    const indexAttribute = new Uint32Array(faceCount * 3);
    for (let faceIndex = 0; faceIndex < faceCount; faceIndex += 1) {
      const sourceIndex = (faceStart + faceIndex) * 3;
      const targetIndex = faceIndex * 3;
      indexAttribute[targetIndex] = Number(model.mesh_face[sourceIndex] ?? 0);
      indexAttribute[targetIndex + 1] = Number(model.mesh_face[sourceIndex + 1] ?? 0);
      indexAttribute[targetIndex + 2] = Number(model.mesh_face[sourceIndex + 2] ?? 0);
    }

    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new Float32BufferAttribute(positionAttribute, 3));
    geometry.setIndex(new Uint32BufferAttribute(indexAttribute, 1));
    geometry.computeVertexNormals();
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    meshGeometryCache.set(meshId, geometry);
    return geometry;
  };

  const getMaterialForGeom = (geom: any, sourceGeom: any | null = null): MeshPhongMaterial => {
    const sourceBodyId = sourceGeom === null ? Number.NaN : Number(sourceGeom.bodyid);
    const bodyId = Number.isFinite(sourceBodyId) && sourceBodyId >= 0 ? sourceBodyId : Number(geom.bodyid);
    const bodyName =
      Number.isFinite(bodyId) && bodyId >= 0
        ? String(mujocoApi.mj_id2name(model, mujocoApi.mjtObj.mjOBJ_BODY.value, bodyId) ?? "")
        : "";
    const geomName = geom.name === undefined ? "" : String(geom.name);
    const sourceMeshId = sourceGeom === null ? Number.NaN : Number(sourceGeom.dataid);
    const meshId = Number.isFinite(sourceMeshId) && sourceMeshId >= 0 ? sourceMeshId : Number(geom.dataid);
    const meshName = meshId >= 0 && meshId < model.nmesh ? String(model.mesh(meshId).name ?? "") : "";
    const cacheKey = `${bodyName}:${geomName}:${meshName}:${geom.type}`;
    const cached = materialByKey.get(cacheKey);
    if (cached !== undefined) {
      return cached as MeshPhongMaterial;
    }

    if (geomName === "floor" || geom.type === mujocoApi.mjtGeom.mjGEOM_PLANE.value) {
      return floorMaterial;
    }

    const style: BodyVisualStyle | null = resolveBodyVisualStyle(
      options.profile,
      bodyName,
      meshName,
      geomName,
    );
    const materialColor = (() => {
      if (style !== null) {
        return style.color;
      }

      return geom.rgba[3] < 1 ? "#93c5fd" : "#e2e8f0";
    })();

    const material = new MeshPhongMaterial({
      color: new Color(materialColor),
      transparent: geom.rgba[3] < 1,
      opacity: geom.rgba[3],
      side: DoubleSide,
      shininess: 18,
      specular: new Color("#111827"),
    });
    materialByKey.set(cacheKey, material);
    return material;
  };

  const syncSceneFromCurrentData = (): void => {
    mujocoApi.mjv_updateScene(
      model,
      data,
      mjvOption,
      mjvPerturb,
      mjvCamera,
      mujocoApi.mjtCatBit.mjCAT_ALL.value,
      mjvScene,
    );

    const geoms = mjvScene.geoms;
    for (let geomIndex = 0; geomIndex < geoms.size(); geomIndex += 1) {
      const geom = geoms.get(geomIndex);
      let mesh = objectByGeomIndex.get(geomIndex);
      if (mesh === undefined) {
        let sourceGeom: any | null = null;
        let geometry: BufferGeometry;
        if (geom.type === mujocoApi.mjtGeom.mjGEOM_MESH.value) {
          sourceGeom = geom.objtype === mujocoApi.mjtObj.mjOBJ_GEOM.value ? model.geom(geom.objid) : null;
          const meshId = sourceGeom === null ? geom.dataid : sourceGeom.dataid;
          geometry = buildCompiledMeshGeometry(meshId);
        } else {
          geometry = buildPrimitiveGeometry(geom.type, geom.size);
        }

        mesh = new Mesh(geometry, getMaterialForGeom(geom, sourceGeom));
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        objectByGeomIndex.set(geomIndex, mesh);
        scene.add(mesh);
      }

      mesh.matrixAutoUpdate = false;
      mesh.matrix.copy(matrixFromMujocoGeom(geom));
      mesh.matrixWorldNeedsUpdate = true;
      geom.delete();
    }
    geoms.delete();
  };

  const applyModelPose = (
    qpos: readonly number[],
    sourceLabel: string,
    frameIndex: number | null,
    timeS: number | null,
    endpointEvaluation: TransportPayloadV0["endpoint_evaluation"] | null,
    inputOverlay: ProductViewerState["inputOverlay"],
    candidate: ViewerPayloadCandidate | null = null,
  ): void => {
    const sceneApplyStartedMs = frameTiming.now();
    data.qpos.set(qpos);
    mujocoApi.mj_forward(model, data);
    syncSceneFromCurrentData();
    if (candidate !== null) {
      frameTiming.recordSceneApplied(candidate, frameTiming.now() - sceneApplyStartedMs);
    }
    updateStatus({
      status: "ready",
      sourceLabel,
      qposStatus: "ready",
      qposError: null,
      currentFrameIndex: frameIndex,
      currentTimestampS: timeS,
      currentQpos: Array.from(qpos),
      endpointEvaluation,
      inputOverlay,
      modelNq: model.nq,
      modelNv: model.nv,
      modelNgeom: model.ngeom,
      modelNmesh: model.nmesh,
    });
  };

  let startupPoseSourceLabel = options.profile.initialPoseSourceLabel;
  const applyStartupPose = (): void => {
    applyModelPose(startupQpos, startupPoseSourceLabel, null, null, null, null);
  };

  const applyTransportPayload = (candidate: ViewerPayloadCandidate): void => {
    const payload = candidate.payload;
    const endpointEvaluation = payload.endpoint_evaluation ?? null;
    const inputOverlay = buildProductViewerInputOverlayState(payload);
    const qposResolution = resolveTransportQpos(payload, model.nq, options.profile);
    if (qposResolution.status !== "ready" || qposResolution.qpos === null) {
      updateStatus({
        status: "warning",
        sourceLabel: qposResolution.sourceLabel,
        qposStatus: qposResolution.status,
        qposError: qposResolution.errorMessage,
        currentFrameIndex: qposResolution.currentFrameIndex,
        currentTimestampS: qposResolution.currentTimestampS,
        currentQpos: null,
        currentQposText: "[]",
        endpointEvaluation,
        inputOverlay,
      });
      return;
    }

    applyModelPose(
      qposResolution.qpos,
      qposResolution.sourceLabel,
      qposResolution.currentFrameIndex,
      qposResolution.currentTimestampS,
      endpointEvaluation,
      inputOverlay,
      candidate,
    );
  };

  const syncToLatestSource = (): void => {
    const candidate = frameTiming.takeLatestCandidate();
    if (candidate !== null) {
      applyTransportPayload(candidate);
      return;
    }

    applyStartupPose();
  };

  const setCanvasSize = (): void => {
    const width = Math.max(640, options.canvas.clientWidth || DEFAULT_WIDTH);
    const height = Math.max(480, options.canvas.clientHeight || DEFAULT_HEIGHT);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };

  const animate = (): void => {
    if (disposed) {
      return;
    }

    const candidate = frameTiming.takeLatestCandidate();
    if (candidate !== null) {
      applyTransportPayload(candidate);
    }
    controls.update();
    renderer.render(scene, camera);
    frameHandle = window.requestAnimationFrame(animate);
  };

  const startWebSocketClient = (): void => {
    if (websocketUrl === null) {
      updateStatus({
        connectionStatus: "disabled",
      });
      return;
    }

    websocketClient = createViewerWebSocketClient({
      url: websocketUrl,
      onOpen() {
        updateStatus({ connectionStatus: "open" });
      },
      onClose() {
        updateStatus({ connectionStatus: "closed" });
      },
      onConnectionError(error) {
        updateStatus({
          connectionStatus: "error",
          status: "warning",
          qposStatus: "unavailable",
          qposError: error instanceof Error ? error.message : "viewer WebSocket connection error",
        });
      },
      onPayload(payload, observation) {
        frameTiming.receive(payload, observation);
        const qposResolution = resolveTransportQpos(payload, model.nq, options.profile);
        if (qposResolution.status !== "ready" || qposResolution.qpos === null) {
          frameTiming.recordCompatibilityInvalidIngress();
          updateStatus({
            status: "warning",
            sourceLabel: qposResolution.sourceLabel,
            qposStatus: qposResolution.status,
            qposError: qposResolution.errorMessage,
            currentFrameIndex: qposResolution.currentFrameIndex,
            currentTimestampS: qposResolution.currentTimestampS,
            currentQpos: null,
            currentQposText: "[]",
            endpointEvaluation: payload.endpoint_evaluation ?? null,
            inputOverlay: buildProductViewerInputOverlayState(payload),
          });
          return;
        }
        frameTiming.acceptLatestCandidate(payload, observation);
      },
      onPayloadError(error) {
        frameTiming.recordParseError();
        updateStatus({
          status: "warning",
          qposStatus: "invalid",
          qposError: error.message,
          currentQpos: null,
          currentQposText: "[]",
        });
      },
    });

    updateStatus({ connectionStatus: "connecting" });
    websocketClient.start();
  };

  const initializeModel = async (): Promise<void> => {
    updateStatus({ status: "loading", connectionStatus: websocketUrl === null ? "disabled" : "connecting" });

    mujocoApi = await loadMujocoWasm();

    const response = await fetch(options.profile.modelUrl);
    if (!response.ok) {
      throw new Error(`failed to fetch ${options.profile.modelUrl}: ${response.status} ${response.statusText}`);
    }

    const xml = await response.text();
    const vfs = new mujocoApi.MjVFS();
    try {
      for (const [vfsPath, assetUrl] of options.profile.vfsAssets.entries()) {
        const assetResponse = await fetch(assetUrl);
        if (!assetResponse.ok) {
          throw new Error(`failed to fetch ${assetUrl}: ${assetResponse.status} ${assetResponse.statusText}`);
        }
        vfs.addBuffer(vfsPath, new Uint8Array(await assetResponse.arrayBuffer()));
      }

      model = mujocoApi.MjModel.from_xml_string(xml, vfs);
      data = new mujocoApi.MjData(model);
      if (model.nq !== options.profile.qposDimension) {
        throw new Error(
          `viewer model/profile qpos dimension mismatch: expected ${options.profile.qposDimension}, got ${model.nq}`,
        );
      }
      const modelJointNames = Array.from(
        { length: Number(model.njnt) },
        (_, jointIndex) =>
          mujocoApi.mj_id2name(
            model,
            mujocoApi.mjtObj.mjOBJ_JOINT.value,
            jointIndex,
          ) ?? "",
      );
      if (
        modelJointNames.length !== options.profile.jointNames.length ||
        modelJointNames.some((name, index) => name !== options.profile.jointNames[index])
      ) {
        throw new Error(
          `viewer model/profile joint name/order mismatch: expected ${options.profile.jointNames.join(",")}, got ${modelJointNames.join(",")}`,
        );
      }
      const initialKeyframe = resolveNamedInitialKeyframe(model, options.profile);
      startupQpos = Array.from(initialKeyframe.qpos);
      startupPoseSourceLabel = initialKeyframe.sourceLabel;
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

      for (let meshIndex = 0; meshIndex < model.nmesh; meshIndex += 1) {
        const meshName = mujocoApi.mj_id2name(model, mujocoApi.mjtObj.mjOBJ_MESH.value, meshIndex);
        if (meshName !== null) {
          modelMeshNameById.set(meshIndex, meshName);
        }
      }

      data.qpos.set(startupQpos);
      mujocoApi.mj_forward(model, data);
      mjvScene = new mujocoApi.MjvScene(model, MAX_GEOMS);
      mjvOption = new mujocoApi.MjvOption();
      mjvPerturb = new mujocoApi.MjvPerturb();
      mjvCamera = new mujocoApi.MjvCamera();

      updateStatus({
        robotProfileId: options.profile.profileId,
        modelContractVersion: options.profile.modelContractVersion,
        modelPath: options.profile.modelUrl,
        fixturePath: options.profile.fixtureUrl,
        modelNq: model.nq,
        modelNv: model.nv,
        modelNgeom: model.ngeom,
        modelNmesh: model.nmesh,
      });

      hasLoaded = true;
      syncToLatestSource();
      updateStatus({
        status: "ready",
        sceneSummaryText: `loaded ${model.ngeom} geoms and ${model.nmesh} compiled meshes`,
      });
    } finally {
      vfs.delete();
    }
  };

  return {
    async start() {
      if (hasLoaded || disposed) {
        return;
      }

      try {
        await initializeModel();
        startWebSocketClient();
        setCanvasSize();
        updateStatus({
          statusText: formatViewerStatusText(state),
        });
        window.addEventListener("resize", setCanvasSize);
        frameHandle = window.requestAnimationFrame(animate);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        updateStatus({
          status: "error",
          qposStatus: "unavailable",
          qposError: message,
          sceneSummaryText: message,
          statusText: [
            `renderer mode: wasm-scene`,
            `robot profile: ${options.profile.profileId}`,
            `model path: ${options.profile.modelUrl}`,
            `fixture path: ${options.profile.fixtureUrl}`,
            `error: ${message}`,
          ].join("\n"),
        });
        options.onError?.(error instanceof Error ? error : new Error(message));
      }
    },
    dispose() {
      disposed = true;
      frameTiming.dispose();
      if (frameHandle !== null) {
        window.cancelAnimationFrame(frameHandle);
        frameHandle = null;
      }
      window.removeEventListener("resize", setCanvasSize);
      websocketClient?.stop();
      websocketClient = null;
      meshGeometryCache.clear();
      objectByGeomIndex.clear();
      materialByKey.clear();
      modelMeshNameById.clear();
      floorTexture.dispose();
      floorMaterial.dispose();
      renderer.dispose();
    },
  };
}
