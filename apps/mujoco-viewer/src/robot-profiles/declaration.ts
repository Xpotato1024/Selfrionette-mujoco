import type {
  ViewerAxisVisualStyle,
  ViewerBodyVisualStyle,
  ViewerRobotProfile,
} from "./types.js";
import type { TransportPayloadV0 } from "../types/transportPayload.js";

export const VIEWER_ROBOT_DECLARATION_SCHEMA_VERSION = "viewer-robot-declaration/v1" as const;

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, name: string): JsonRecord {
  if (!isRecord(value)) {
    throw new Error(`${name} must be an object`);
  }
  return value;
}

function requireExactKeys(value: JsonRecord, expected: readonly string[], name: string): void {
  const actual = Object.keys(value).sort();
  const wanted = Array.from(expected).sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    throw new Error(`${name} keys mismatch: expected ${wanted.join(",")}, got ${actual.join(",")}`);
  }
}

function requireString(value: unknown, name: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${name} must be a non-empty string`);
  }
  return value;
}

function requirePositiveInteger(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

function requireLocalUrl(value: unknown, name: string): string {
  const url = requireString(value, name);
  if (!url.startsWith("/") || url.startsWith("//") || url.split("/").includes("..")) {
    throw new Error(`${name} must be a local absolute-path URL`);
  }
  return url;
}

function requireResourcePath(value: unknown, name: string): string {
  const path = requireString(value, name);
  if (path.startsWith("/") || path.includes("\\") || path.split("/").includes("..")) {
    throw new Error(`${name} must be a repository-relative POSIX path`);
  }
  return path;
}

function requireArray(value: unknown, name: string): readonly unknown[] {
  if (!Array.isArray(value)) {
    throw new Error(`${name} must be an array`);
  }
  return value;
}

function requireUnique(values: readonly string[], name: string): void {
  if (new Set(values).size !== values.length) {
    throw new Error(`${name} must be unique`);
  }
}

const ROOT_KEYS = [
  "schemaVersion",
  "profileId",
  "profileContractVersion",
  "modelContractVersion",
  "modelUrl",
  "modelResourcePath",
  "initialKeyframeName",
  "initialPoseSourceLabel",
  "fixtureUrl",
  "vfsAssets",
  "visualStyleSelection",
  "bodyVisualStyles",
  "axisVisualStyles",
  "jointNames",
  "qposDimension",
] as const;

export function decodeViewerRobotDeclaration(value: unknown): ViewerRobotProfile {
  const root = requireRecord(value, "viewer robot declaration");
  requireExactKeys(root, ROOT_KEYS, "viewer robot declaration");
  const schemaVersion = requireString(root.schemaVersion, "schemaVersion");
  if (schemaVersion !== VIEWER_ROBOT_DECLARATION_SCHEMA_VERSION) {
    throw new Error(`unsupported viewer robot declaration schema version: ${schemaVersion}`);
  }

  const vfsAssets = new Map<string, string>();
  const vfsResourcePaths = new Map<string, string>();
  for (const [index, raw] of requireArray(root.vfsAssets, "vfsAssets").entries()) {
    const item = requireRecord(raw, `vfsAssets[${index}]`);
    requireExactKeys(item, ["vfsPath", "resourcePath", "url"], `vfsAssets[${index}]`);
    const vfsPath = requireString(item.vfsPath, `vfsAssets[${index}].vfsPath`);
    if (vfsPath.startsWith("/") || vfsPath.split("/").includes("..")) {
      throw new Error(`vfsAssets[${index}].vfsPath must not escape the virtual root`);
    }
    if (vfsAssets.has(vfsPath)) {
      throw new Error(`duplicate viewer VFS path: ${vfsPath}`);
    }
    vfsResourcePaths.set(
      vfsPath,
      requireResourcePath(item.resourcePath, `vfsAssets[${index}].resourcePath`),
    );
    vfsAssets.set(vfsPath, requireLocalUrl(item.url, `vfsAssets[${index}].url`));
  }

  const bodyVisualStyles: Record<string, ViewerBodyVisualStyle> = {};
  for (const [index, raw] of requireArray(root.bodyVisualStyles, "bodyVisualStyles").entries()) {
    const item = requireRecord(raw, `bodyVisualStyles[${index}]`);
    requireExactKeys(item, ["key", "color", "label", "detail"], `bodyVisualStyles[${index}]`);
    const key = requireString(item.key, `bodyVisualStyles[${index}].key`);
    if (bodyVisualStyles[key] !== undefined) {
      throw new Error(`duplicate viewer body style key: ${key}`);
    }
    bodyVisualStyles[key] = Object.freeze({
      color: requireString(item.color, `bodyVisualStyles[${index}].color`),
      label: requireString(item.label, `bodyVisualStyles[${index}].label`),
      detail: requireString(item.detail, `bodyVisualStyles[${index}].detail`),
    });
  }

  const visualStyleSelection = new Map<string, string>();
  for (const [index, raw] of requireArray(root.visualStyleSelection, "visualStyleSelection").entries()) {
    const item = requireRecord(raw, `visualStyleSelection[${index}]`);
    requireExactKeys(item, ["match", "styleKey"], `visualStyleSelection[${index}]`);
    const match = requireString(item.match, `visualStyleSelection[${index}].match`);
    const styleKey = requireString(item.styleKey, `visualStyleSelection[${index}].styleKey`);
    if (visualStyleSelection.has(match)) {
      throw new Error(`duplicate viewer visual style match: ${match}`);
    }
    if (bodyVisualStyles[styleKey] === undefined) {
      throw new Error(`viewer visual style selection references unknown style key: ${styleKey}`);
    }
    visualStyleSelection.set(match, styleKey);
  }

  const axisVisualStyles: ViewerAxisVisualStyle[] = requireArray(
    root.axisVisualStyles,
    "axisVisualStyles",
  ).map((raw, index) => {
    const item = requireRecord(raw, `axisVisualStyles[${index}]`);
    requireExactKeys(item, ["color", "label", "detail"], `axisVisualStyles[${index}]`);
    return Object.freeze({
      color: requireString(item.color, `axisVisualStyles[${index}].color`),
      label: requireString(item.label, `axisVisualStyles[${index}].label`),
      detail: requireString(item.detail, `axisVisualStyles[${index}].detail`),
    });
  });

  const jointNames = requireArray(root.jointNames, "jointNames").map((value, index) =>
    requireString(value, `jointNames[${index}]`),
  );
  if (jointNames.length === 0) {
    throw new Error("jointNames must not be empty");
  }
  requireUnique(jointNames, "jointNames");

  return Object.freeze({
    schemaVersion: VIEWER_ROBOT_DECLARATION_SCHEMA_VERSION,
    profileId: requireString(root.profileId, "profileId"),
    profileContractVersion: requirePositiveInteger(root.profileContractVersion, "profileContractVersion"),
    modelContractVersion: requireString(root.modelContractVersion, "modelContractVersion"),
    modelUrl: requireLocalUrl(root.modelUrl, "modelUrl"),
    modelResourcePath: requireResourcePath(root.modelResourcePath, "modelResourcePath"),
    initialKeyframeName: requireString(root.initialKeyframeName, "initialKeyframeName"),
    initialPoseSourceLabel: requireString(root.initialPoseSourceLabel, "initialPoseSourceLabel"),
    fixtureUrl: requireLocalUrl(root.fixtureUrl, "fixtureUrl"),
    vfsAssets,
    vfsResourcePaths,
    visualStyleSelection,
    bodyVisualStyles: Object.freeze(bodyVisualStyles),
    axisVisualStyles: Object.freeze(axisVisualStyles),
    jointNames: Object.freeze(jointNames),
    qposDimension: requirePositiveInteger(root.qposDimension, "qposDimension"),
  });
}

export function viewerRobotProfileFromPayload(payload: TransportPayloadV0): ViewerRobotProfile {
  const profile = decodeViewerRobotDeclaration(payload.metadata.viewer_robot_declaration);
  const metadata = payload.metadata;
  if (metadata.robot_profile_id !== profile.profileId) {
    throw new Error("backend/viewer declaration robot profile mismatch");
  }
  if (metadata.model_contract_version !== profile.modelContractVersion) {
    throw new Error("backend/viewer declaration model contract mismatch");
  }
  if (metadata.robot_qpos_dimension !== profile.qposDimension) {
    throw new Error("backend/viewer declaration qpos dimension mismatch");
  }
  if (
    !Array.isArray(metadata.robot_joint_names) ||
    metadata.robot_joint_names.length !== profile.jointNames.length ||
    metadata.robot_joint_names.some((name, index) => name !== profile.jointNames[index])
  ) {
    throw new Error("backend/viewer declaration joint name/order mismatch");
  }
  return profile;
}

export function viewerRobotProfileCanonicalJson(profile: ViewerRobotProfile): string {
  return JSON.stringify({
    schemaVersion: profile.schemaVersion,
    profileId: profile.profileId,
    profileContractVersion: profile.profileContractVersion,
    modelContractVersion: profile.modelContractVersion,
    modelUrl: profile.modelUrl,
    modelResourcePath: profile.modelResourcePath,
    initialKeyframeName: profile.initialKeyframeName,
    initialPoseSourceLabel: profile.initialPoseSourceLabel,
    fixtureUrl: profile.fixtureUrl,
    vfsAssets: Array.from(profile.vfsAssets.entries()).map(([vfsPath, url]) => ({
      vfsPath,
      resourcePath: profile.vfsResourcePaths.get(vfsPath),
      url,
    })),
    visualStyleSelection: Array.from(profile.visualStyleSelection.entries()),
    bodyVisualStyles: profile.bodyVisualStyles,
    axisVisualStyles: profile.axisVisualStyles,
    jointNames: profile.jointNames,
    qposDimension: profile.qposDimension,
  });
}

export async function loadViewerRobotDeclaration(
  url: string,
  fetcher: typeof fetch = fetch,
): Promise<ViewerRobotProfile> {
  const response = await fetcher(url);
  if (!response.ok) {
    throw new Error(`failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }
  return decodeViewerRobotDeclaration(await response.json());
}
