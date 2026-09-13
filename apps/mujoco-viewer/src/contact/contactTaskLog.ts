import type { QuaternionWXYZ, Vector3 } from "../types/transportPayload.js";

export type ContactTaskPresentationStatus = "available" | "unavailable" | "stale";
export type ContactTaskSourceKind = "runtime_capture" | "synthetic_fixture";
export type ContactTaskInputSource = "none" | "transport_metadata" | "offline_log" | "offline_payload";

export interface ContactTaskRobotProfileIdentity {
  profileId: string;
  profileContractVersion: number;
}

export interface ContactTaskPayloadContext {
  timeS: number;
  frameIndex: number;
}

export interface ContactTaskIdentity {
  name: string;
  version: number;
}

export interface ContactTaskLogBinding {
  manifest_digest: string;
  object_identity: ContactTaskIdentity;
  presentation_identity: string;
  robot_bundle: { plugin_id: string; contract_version: number };
  scene_identity: ContactTaskIdentity;
  signal_manifest_digest: string;
  source_kind: ContactTaskSourceKind;
  trial: {
    trial_id: string;
    attempt_index: number;
    repetition_index: number;
    retry_of_trial_id: string | null;
  };
}

export interface ContactTaskPresentationContact {
  contactIdentity: string;
  pointWorldM: Vector3;
  normalWorld: Vector3;
  penetrationM: number;
}

export interface ContactTaskPresentationV1 {
  status: ContactTaskPresentationStatus;
  reason: string | null;
  sourceKind: ContactTaskSourceKind | null;
  evidenceNotice: string | null;
  binding: ContactTaskLogBinding | null;
  sequenceIndex: number | null;
  payloadAgeS: number | null;
  maxAgeS: number | null;
  sample: {
    elapsedTimeS: number;
    sampleTimeS: number;
    simulationTimeS: number;
    frameIndex: number | null;
  } | null;
  cube: {
    identity: ContactTaskIdentity;
    presentationIdentity: string;
    shape: "box";
    halfSizeM: Vector3;
    rgba: [number, number, number, number];
    positionWorldM: Vector3;
    orientationWXYZ: QuaternionWXYZ;
  } | null;
  contacts: ContactTaskPresentationContact[];
  rawEvidence: {
    status: string;
    reason: string | null;
    contactCount: number | null;
    forceWorldN: Vector3 | null;
  } | null;
  derivedForce: {
    status: string;
    sourceStatus: string | null;
    frame: "mujoco_world" | "tool";
    forceN: Vector3 | null;
    rawForceWorldN: Vector3 | null;
    unit: string;
    signConvention: string;
    filtered: boolean;
    deadbanded: boolean;
    rateLimited: boolean;
    clamped: boolean;
    reason: string | null;
  } | null;
  taskState: { phase: string; classification: string; reason: string | null } | null;
  outcome: {
    phase: string;
    classification: string;
    reason: string | null;
    completionTimeS: number | null;
    observationsCount: number;
  } | null;
}

const PRESENTATION_SCHEMA_VERSION = "contact-task-presentation/v1";
const LOG_SCHEMA_VERSION = "contact-task-log/v1";
const LOG_PROVENANCE = "runtime_contact_task_log/v1";
const EVIDENCE_SCHEMA_VERSION = "contact-evidence/v1";
const FORCE_SCHEMA_VERSION = "virtual-reaction-force/v1";
const OUTCOME_SCHEMA_VERSION = "contact-task-outcome/v1";
const SYNTHETIC_NOTICE = "決定的に生成した合成fixtureです。MuJoCoから取得した接触証拠ではありません。";
const SHA256_PATTERN = /^sha256:[0-9a-f]{64}$/;

type JsonRecord = Record<string, unknown>;

const CONTACT_TASK_PHASES = [
  "ready",
  "approach",
  "first_contact",
  "press",
  "hold",
  "success",
  "failure",
  "technical_invalid",
] as const;
type ContactTaskPhase = (typeof CONTACT_TASK_PHASES)[number];

const CONTACT_TASK_CLASSIFICATIONS = [
  "success",
  "failure",
  "technical_invalid",
  "running",
] as const;
type ContactTaskClassification = (typeof CONTACT_TASK_CLASSIFICATIONS)[number];

interface ParsedTaskState {
  phase: ContactTaskPhase;
  classification: ContactTaskClassification;
  reason: string | null;
}

interface ParsedJsonLine {
  value: JsonRecord;
  rawTopLevelValues: Map<string, string>;
}

interface ParsedManifest {
  document: JsonRecord;
  sceneIdentity: ContactTaskIdentity;
  objectIdentity: ContactTaskIdentity;
  presentationIdentity: string;
  robotBundle: { plugin_id: string; contract_version: number };
  cube: {
    identity: ContactTaskIdentity;
    shape: "box";
    halfSizeM: Vector3;
    rgba: [number, number, number, number];
  };
}

interface ParsedSignalManifest {
  maxInterSampleGapS: number;
  outputFrame: "mujoco_world" | "tool";
  sourceSceneIdentity: ContactTaskIdentity;
  sourceObjectIdentity: ContactTaskIdentity;
}

interface ParsedRawEvidence {
  document: JsonRecord;
  status: string;
  reason: string | null;
  sampleTimeS: number;
  simulationTimeS: number;
  frameIndex: number | null;
  contactCount: number | null;
  forceWorldN: Vector3 | null;
  targetContacts: ContactTaskPresentationContact[];
}

interface ParsedDerivedForce {
  document: JsonRecord;
  status: string;
  sourceStatus: string | null;
  frame: "mujoco_world" | "tool";
  forceN: Vector3 | null;
  rawForceWorldN: Vector3 | null;
  filtered: boolean;
  deadbanded: boolean;
  rateLimited: boolean;
  clamped: boolean;
  reason: string | null;
}

function record(value: unknown, label: string): JsonRecord {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(label + " must be an object");
  }
  return value as JsonRecord;
}

function exactKeys(value: unknown, keys: readonly string[], label: string): JsonRecord {
  const object = record(value, label);
  const actual = Object.keys(object).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new Error(label + " has unknown or missing fields");
  }
  return object;
}

function stringValue(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(label + " must be a non-empty string");
  }
  return value;
}

function nullableString(value: unknown, label: string): string | null {
  if (value === null) {
    return null;
  }
  if (typeof value !== "string") {
    throw new Error(label + " must be a string or null");
  }
  return value;
}

function finiteNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(label + " must be finite");
  }
  return value;
}

function nonNegativeNumber(value: unknown, label: string): number {
  const result = finiteNumber(value, label);
  if (result < 0) {
    throw new Error(label + " must be non-negative");
  }
  return result;
}

function integer(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value)) {
    throw new Error(label + " must be a safe integer");
  }
  return value;
}

function nonNegativeInteger(value: unknown, label: string): number {
  const result = integer(value, label);
  if (result < 0) {
    throw new Error(label + " must be non-negative");
  }
  return result;
}

function booleanValue(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") {
    throw new Error(label + " must be a boolean");
  }
  return value;
}

function vector3(value: unknown, label: string): Vector3 {
  if (!Array.isArray(value) || value.length !== 3) {
    throw new Error(label + " must contain three values");
  }
  return [
    finiteNumber(value[0], label + "[0]"),
    finiteNumber(value[1], label + "[1]"),
    finiteNumber(value[2], label + "[2]"),
  ];
}

function quaternionWXYZ(value: unknown, label: string): QuaternionWXYZ {
  if (!Array.isArray(value) || value.length !== 4) {
    throw new Error(label + " must contain four values");
  }
  const result: QuaternionWXYZ = [
    finiteNumber(value[0], label + "[0]"),
    finiteNumber(value[1], label + "[1]"),
    finiteNumber(value[2], label + "[2]"),
    finiteNumber(value[3], label + "[3]"),
  ];
  const norm = Math.hypot(...result);
  if (norm < 1e-12 || Math.abs(norm - 1) > 1e-6) {
    throw new Error(label + " must be a unit quaternion");
  }
  return result;
}

function identity(value: unknown, label: string): ContactTaskIdentity {
  const object = exactKeys(value, ["name", "version"], label);
  return {
    name: stringValue(object.name, label + ".name"),
    version: nonNegativeInteger(object.version, label + ".version"),
  };
}

function sameJson(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function unavailableContactTaskPresentation(reason: string): ContactTaskPresentationV1 {
  return {
    status: "unavailable",
    reason,
    sourceKind: null,
    evidenceNotice: null,
    binding: null,
    sequenceIndex: null,
    payloadAgeS: null,
    maxAgeS: null,
    sample: null,
    cube: null,
    contacts: [],
    rawEvidence: null,
    derivedForce: null,
    taskState: null,
    outcome: null,
  };
}

function parseSourceKind(value: unknown): ContactTaskSourceKind {
  if (value !== "runtime_capture" && value !== "synthetic_fixture") {
    throw new Error("contact source_kind is unsupported");
  }
  return value;
}

function parseTrial(value: unknown): ContactTaskLogBinding["trial"] {
  const trial = exactKeys(
    value,
    ["attempt_index", "repetition_index", "retry_of_trial_id", "trial_id"],
    "contact trial identity",
  );
  return {
    trial_id: stringValue(trial.trial_id, "trial_id"),
    attempt_index: nonNegativeInteger(trial.attempt_index, "attempt_index"),
    repetition_index: nonNegativeInteger(trial.repetition_index, "repetition_index"),
    retry_of_trial_id: nullableString(trial.retry_of_trial_id, "retry_of_trial_id"),
  };
}

function parseBinding(value: unknown): ContactTaskLogBinding {
  const binding = exactKeys(
    value,
    [
      "manifest_digest",
      "object_identity",
      "presentation_identity",
      "robot_bundle",
      "scene_identity",
      "signal_manifest_digest",
      "source_kind",
      "trial",
    ],
    "contact log binding",
  );
  const manifestDigest = stringValue(binding.manifest_digest, "manifest_digest");
  const signalDigest = stringValue(binding.signal_manifest_digest, "signal_manifest_digest");
  if (!SHA256_PATTERN.test(manifestDigest) || !SHA256_PATTERN.test(signalDigest)) {
    throw new Error("contact log binding contains an invalid digest");
  }
  const robotBundle = exactKeys(
    binding.robot_bundle,
    ["contract_version", "plugin_id"],
    "contact robot bundle identity",
  );
  return {
    manifest_digest: manifestDigest,
    object_identity: identity(binding.object_identity, "object_identity"),
    presentation_identity: stringValue(binding.presentation_identity, "presentation_identity"),
    robot_bundle: {
      plugin_id: stringValue(robotBundle.plugin_id, "robot_bundle.plugin_id"),
      contract_version: nonNegativeInteger(
        robotBundle.contract_version,
        "robot_bundle.contract_version",
      ),
    },
    scene_identity: identity(binding.scene_identity, "scene_identity"),
    signal_manifest_digest: signalDigest,
    source_kind: parseSourceKind(binding.source_kind),
    trial: parseTrial(binding.trial),
  };
}

function parseManifest(value: unknown, binding: ContactTaskLogBinding): ParsedManifest {
  const manifest = exactKeys(
    value,
    [
      "contract_version",
      "environment",
      "evaluators",
      "robot_bundle",
      "scene",
      "schema_version",
      "software_revision_identity",
      "task",
    ],
    "contact task manifest",
  );
  if (manifest.schema_version !== "contact-task-manifest/v1" || manifest.contract_version !== 1) {
    throw new Error("contact task manifest version is unsupported");
  }
  const robotBundle = exactKeys(
    manifest.robot_bundle,
    ["contract_version", "plugin_id"],
    "manifest robot bundle",
  );
  const parsedRobotBundle = {
    plugin_id: stringValue(robotBundle.plugin_id, "manifest.robot_bundle.plugin_id"),
    contract_version: nonNegativeInteger(
      robotBundle.contract_version,
      "manifest.robot_bundle.contract_version",
    ),
  };
  if (!sameJson(parsedRobotBundle, binding.robot_bundle)) {
    throw new Error("contact robot bundle does not match the binding");
  }

  const scene = record(manifest.scene, "manifest.scene");
  const sceneIdentity = identity(scene.identity, "manifest.scene.identity");
  const object = record(scene.object, "manifest.scene.object");
  const objectIdentity = identity(object.identity, "manifest.scene.object.identity");
  const presentation = record(scene.presentation, "manifest.scene.presentation");
  const presentationIdentity = stringValue(
    presentation.visual_feedback_identity,
    "manifest.scene.presentation.visual_feedback_identity",
  );
  if (
    sceneIdentity.name !== "contact_cube_scene" ||
    sceneIdentity.version !== 1 ||
    objectIdentity.name !== "contact_cube" ||
    objectIdentity.version !== 1 ||
    presentationIdentity !== "contact-cube/v1"
  ) {
    throw new Error("unsupported contact scene, object, or presentation identity");
  }
  if (
    !sameJson(sceneIdentity, binding.scene_identity) ||
    !sameJson(objectIdentity, binding.object_identity) ||
    presentationIdentity !== binding.presentation_identity
  ) {
    throw new Error("contact scene identity does not match the binding");
  }
  if (object.shape !== "box") {
    throw new Error("contact cube shape is unsupported");
  }
  const halfSizeM = vector3(object.size_m, "manifest.scene.object.size_m");
  if (halfSizeM.some((size) => size <= 0)) {
    throw new Error("contact cube half-size must be positive");
  }
  const material = record(object.material, "manifest.scene.object.material");
  if (!Array.isArray(material.rgba) || material.rgba.length !== 4) {
    throw new Error("contact cube rgba must contain four values");
  }
  const rgba: [number, number, number, number] = [
    finiteNumber(material.rgba[0], "contact cube rgba[0]"),
    finiteNumber(material.rgba[1], "contact cube rgba[1]"),
    finiteNumber(material.rgba[2], "contact cube rgba[2]"),
    finiteNumber(material.rgba[3], "contact cube rgba[3]"),
  ];
  if (rgba.some((channel) => channel < 0 || channel > 1)) {
    throw new Error("contact cube rgba channels must be between zero and one");
  }

  return {
    document: manifest,
    sceneIdentity,
    objectIdentity,
    presentationIdentity,
    robotBundle: parsedRobotBundle,
    cube: { identity: objectIdentity, shape: "box", halfSizeM, rgba },
  };
}

function parseSignalManifest(value: unknown, binding: ContactTaskLogBinding): ParsedSignalManifest {
  const manifest = exactKeys(
    value,
    [
      "config",
      "contract_version",
      "filter_initial_state_policy",
      "filter_order",
      "force_source",
      "identity",
      "no_contact_policy",
      "output_frame_transform_policy",
      "provenance",
      "schema_version",
      "source_contact_manifest_digest",
      "source_object_identity",
      "source_scene_identity",
      "stale_policy",
      "trial_boundary_policy",
    ],
    "virtual reaction-force manifest",
  );
  if (manifest.schema_version !== FORCE_SCHEMA_VERSION || manifest.contract_version !== 1) {
    throw new Error("virtual reaction-force manifest version is unsupported");
  }
  const forceIdentity = identity(manifest.identity, "signal_manifest.identity");
  if (forceIdentity.name !== "virtual_reaction_force" || forceIdentity.version !== 1) {
    throw new Error("virtual reaction-force identity is unsupported");
  }
  if (manifest.source_contact_manifest_digest !== binding.manifest_digest) {
    throw new Error("signal manifest does not reference the bound contact manifest");
  }
  const sourceSceneIdentity = identity(
    manifest.source_scene_identity,
    "signal_manifest.source_scene_identity",
  );
  const sourceObjectIdentity = identity(
    manifest.source_object_identity,
    "signal_manifest.source_object_identity",
  );
  if (
    !sameJson(sourceSceneIdentity, binding.scene_identity) ||
    !sameJson(sourceObjectIdentity, binding.object_identity)
  ) {
    throw new Error("signal manifest scene or object identity does not match the binding");
  }
  const config = exactKeys(
    manifest.config,
    [
      "deadband_n",
      "low_pass_time_constant_s",
      "magnitude_clamp_n",
      "max_inter_sample_gap_s",
      "output_frame",
      "rate_limit_n_per_s",
      "smoothing_window_samples",
    ],
    "signal manifest config",
  );
  const maxInterSampleGapS = finiteNumber(
    config.max_inter_sample_gap_s,
    "signal_manifest.config.max_inter_sample_gap_s",
  );
  if (maxInterSampleGapS <= 0) {
    throw new Error("signal manifest maximum sample gap must be positive");
  }
  if (config.output_frame !== "mujoco_world" && config.output_frame !== "tool") {
    throw new Error("signal manifest output frame is unsupported");
  }
  return {
    maxInterSampleGapS,
    outputFrame: config.output_frame,
    sourceSceneIdentity,
    sourceObjectIdentity,
  };
}

function parseRawEvidence(
  value: unknown,
  binding: ContactTaskLogBinding,
): ParsedRawEvidence {
  const evidence = exactKeys(
    value,
    [
      "aggregate",
      "contacts",
      "frame_index",
      "manifest_digest",
      "object_identity",
      "reason",
      "sample_time_s",
      "scene_identity",
      "schema_version",
      "simulation_time_s",
      "status",
    ],
    "raw contact evidence",
  );
  if (evidence.schema_version !== EVIDENCE_SCHEMA_VERSION) {
    throw new Error("raw contact evidence version is unsupported");
  }
  if (
    evidence.manifest_digest !== binding.manifest_digest ||
    !sameJson(identity(evidence.scene_identity, "raw scene_identity"), binding.scene_identity) ||
    !sameJson(identity(evidence.object_identity, "raw object_identity"), binding.object_identity)
  ) {
    throw new Error("raw contact evidence does not match the contact log binding");
  }
  const status = stringValue(evidence.status, "raw contact evidence status");
  if (
    !["measured", "no_contact", "measurement_unavailable", "invalid_contact", "solver_invalid"].includes(status)
  ) {
    throw new Error("raw contact evidence status is unsupported");
  }
  const sampleTimeS = nonNegativeNumber(evidence.sample_time_s, "raw sample_time_s");
  const simulationTimeS = nonNegativeNumber(evidence.simulation_time_s, "raw simulation_time_s");
  const frameIndex =
    evidence.frame_index === null
      ? null
      : nonNegativeInteger(evidence.frame_index, "raw frame_index");
  const contactsValue = evidence.contacts;
  if (!Array.isArray(contactsValue)) {
    throw new Error("raw contacts must be an array");
  }
  const contacts: ContactTaskPresentationContact[] = contactsValue.map((item, index) => {
    const contact = exactKeys(
      item,
      [
        "body1_id",
        "body1_name",
        "body2_id",
        "body2_name",
        "classification",
        "contact_frame_world",
        "contact_identity",
        "distance_m",
        "force_contact_frame_n",
        "force_status",
        "force_world_n",
        "geom1_id",
        "geom1_name",
        "geom2_id",
        "geom2_name",
        "normal_force_n",
        "normal_world",
        "object_on_tool_force_world_n",
        "penetration_m",
        "point_world_m",
        "resultant_force_n",
        "tangential_force_world_n",
        "tool_on_object_force_world_n",
        "torque_contact_frame_nm",
        "torque_world_nm",
      ],
      "raw contact record " + index,
    );
    const classification = stringValue(contact.classification, "contact classification");
    if (
      !["target_object", "self_contact", "environment_contact", "other_object", "unclassified"].includes(classification)
    ) {
      throw new Error("raw contact classification is unsupported");
    }
    const pointWorldM = vector3(contact.point_world_m, "contact point_world_m");
    const normalWorld = vector3(contact.normal_world, "contact normal_world");
    const normalLength = Math.hypot(...normalWorld);
    if (normalLength < 1e-12 || Math.abs(normalLength - 1) > 1e-5) {
      throw new Error("contact normal must be a unit vector");
    }
    const penetrationM = nonNegativeNumber(contact.penetration_m, "contact penetration_m");
    vector3(contact.object_on_tool_force_world_n, "contact object_on_tool_force_world_n");
    return {
      contactIdentity: stringValue(contact.contact_identity, "contact_identity"),
      pointWorldM,
      normalWorld,
      penetrationM,
    };
  });
  const targetContacts = contacts.filter((_, index) => {
    const item = record(contactsValue[index], "raw contact record");
    return item.classification === "target_object";
  });
  const aggregateValue = evidence.aggregate;
  let contactCount: number | null = null;
  let forceWorldN: Vector3 | null = null;
  if (aggregateValue !== null) {
    const aggregate = exactKeys(
      aggregateValue,
      [
        "contact_count",
        "normal_force_n",
        "object_on_tool_force_world_n",
        "object_on_tool_wrench_world_nm",
        "resultant_force_n",
        "resultant_force_world_n",
        "tangential_force_world_n",
        "tool_on_object_force_world_n",
      ],
      "raw contact aggregate",
    );
    contactCount = nonNegativeInteger(aggregate.contact_count, "aggregate.contact_count");
    finiteNumber(aggregate.normal_force_n, "aggregate.normal_force_n");
    finiteNumber(aggregate.resultant_force_n, "aggregate.resultant_force_n");
    vector3(aggregate.tangential_force_world_n, "aggregate.tangential_force_world_n");
    vector3(aggregate.resultant_force_world_n, "aggregate.resultant_force_world_n");
    vector3(aggregate.tool_on_object_force_world_n, "aggregate.tool_on_object_force_world_n");
    forceWorldN = vector3(
      aggregate.object_on_tool_force_world_n,
      "aggregate.object_on_tool_force_world_n",
    );
    if (!Array.isArray(aggregate.object_on_tool_wrench_world_nm) || aggregate.object_on_tool_wrench_world_nm.length !== 6) {
      throw new Error("aggregate wrench must contain six values");
    }
    aggregate.object_on_tool_wrench_world_nm.forEach((component, index) =>
      finiteNumber(component, "aggregate wrench[" + index + "]"),
    );
  }
  if (status === "measured") {
    if (contactCount === null || contactCount < 1 || targetContacts.length !== contactCount || forceWorldN === null) {
      throw new Error("measured contact evidence has an inconsistent aggregate");
    }
    const summed = [0, 0, 0];
    for (const item of contactsValue) {
      const contact = record(item, "raw target contact");
      if (contact.classification !== "target_object") {
        continue;
      }
      const force = vector3(contact.object_on_tool_force_world_n, "target object_on_tool force");
      summed[0] += force[0];
      summed[1] += force[1];
      summed[2] += force[2];
    }
    if (summed.some((component, index) => Math.abs(component - (forceWorldN?.[index] ?? 0)) > 1e-6)) {
      throw new Error("raw contact aggregate does not equal its target contacts");
    }
  } else if (status === "no_contact") {
    if (
      contactCount !== 0 ||
      targetContacts.length !== 0 ||
      forceWorldN === null ||
      forceWorldN.some((component) => component !== 0)
    ) {
      throw new Error("no-contact evidence must carry an explicit zero aggregate");
    }
  }

  return {
    document: evidence,
    status,
    reason: nullableString(evidence.reason, "raw evidence reason"),
    sampleTimeS,
    simulationTimeS,
    frameIndex,
    contactCount,
    forceWorldN,
    targetContacts,
  };
}

function parseDerivedForce(
  value: unknown,
  binding: ContactTaskLogBinding,
  signalManifest: ParsedSignalManifest,
  rawEvidence: ParsedRawEvidence,
): ParsedDerivedForce {
  const signal = exactKeys(
    value,
    [
      "deadbanded",
      "filtered",
      "force_source",
      "frame_index",
      "identity",
      "manifest_digest",
      "output",
      "provenance",
      "raw_force_world_n",
      "reason",
      "rate_limited",
      "sample_time_s",
      "saturated",
      "schema_version",
      "source_contact_manifest_digest",
      "status",
      "simulation_time_s",
      "trial",
      "unit",
      "sign_convention",
    ],
    "derived reaction-force signal",
  );
  if (signal.schema_version !== FORCE_SCHEMA_VERSION || signal.contract_version !== undefined) {
    throw new Error("derived reaction-force signal version is unsupported");
  }
  const signalIdentity = identity(signal.identity, "derived signal identity");
  if (signalIdentity.name !== "virtual_reaction_force" || signalIdentity.version !== 1) {
    throw new Error("derived reaction-force identity is unsupported");
  }
  if (
    signal.manifest_digest !== binding.signal_manifest_digest ||
    signal.source_contact_manifest_digest !== binding.manifest_digest ||
    !sameJson(parseTrial(signal.trial), binding.trial)
  ) {
    throw new Error("derived reaction-force signal does not match its binding");
  }
  const forceSource = exactKeys(
    signal.force_source,
    ["field", "frame", "identity", "manifest_digest", "sign_convention", "status", "unit"],
    "derived force source",
  );
  if (
    forceSource.field !== "aggregate.object_on_tool_force_world_n" ||
    forceSource.frame !== "mujoco_world" ||
    forceSource.manifest_digest !== binding.manifest_digest ||
    forceSource.sign_convention !== "object_on_tool" ||
    forceSource.unit !== "newton" ||
    !sameJson(identity(forceSource.identity, "force source identity"), {
      name: "contact_evidence",
      version: 1,
    }) ||
    forceSource.status !== rawEvidence.status
  ) {
    throw new Error("derived reaction-force source does not match raw evidence");
  }
  const output = exactKeys(
    signal.output,
    ["force_n", "frame", "raw_force_n", "sign_convention", "unit", "world_to_output_rotation_row_major"],
    "derived force output",
  );
  const outputFrame = output.frame;
  if (outputFrame !== "mujoco_world" && outputFrame !== "tool") {
    throw new Error("derived reaction-force output frame is unsupported");
  }
  if (
    outputFrame !== signalManifest.outputFrame ||
    output.sign_convention !== "object_on_tool" ||
    output.unit !== "newton" ||
    signal.unit !== "newton" ||
    signal.sign_convention !== "object_on_tool"
  ) {
    throw new Error("derived reaction-force output contract is unsupported");
  }
  const status = stringValue(signal.status, "derived signal status");
  if (![
    "active",
    "no_contact",
    "stale",
    "measurement_unavailable",
    "invalid_contact",
    "solver_invalid",
  ].includes(status)) {
    throw new Error("derived reaction-force status is unsupported");
  }
  const frameIndex = signal.frame_index === null ? null : nonNegativeInteger(signal.frame_index, "signal.frame_index");
  const sampleTime = signal.sample_time_s === null ? null : nonNegativeNumber(signal.sample_time_s, "signal.sample_time_s");
  const simulationTime = signal.simulation_time_s === null
    ? null
    : nonNegativeNumber(signal.simulation_time_s, "signal.simulation_time_s");
  if (
    frameIndex !== rawEvidence.frameIndex ||
    sampleTime !== rawEvidence.sampleTimeS ||
    simulationTime !== rawEvidence.simulationTimeS
  ) {
    throw new Error("derived force sample identity does not match raw evidence");
  }
  const forceValue = output.force_n;
  const forceN = forceValue === null ? null : vector3(forceValue, "derived force_n");
  const rawForceWorldN = signal.raw_force_world_n === null
    ? null
    : vector3(signal.raw_force_world_n, "derived raw_force_world_n");
  if (status === "active") {
    if (rawEvidence.status !== "measured" || forceN === null || rawForceWorldN === null) {
      throw new Error("active derived force requires measured raw contact evidence");
    }
    if (
      rawEvidence.forceWorldN === null ||
      rawForceWorldN.some((component, index) => component !== rawEvidence.forceWorldN?.[index])
    ) {
      throw new Error("derived raw force does not preserve the raw contact aggregate");
    }
  } else if (status === "no_contact") {
    if (
      rawEvidence.status !== "no_contact" ||
      forceN === null ||
      forceN.some((component) => component !== 0) ||
      rawForceWorldN === null ||
      rawForceWorldN.some((component) => component !== 0)
    ) {
      throw new Error("no-contact derived force must preserve an explicit zero");
    }
  } else if (forceN !== null) {
    throw new Error("invalid derived force state must not carry a display force");
  }
  const sourceStatus = nullableString(forceSource.status, "force source status");
  return {
    document: signal,
    status,
    sourceStatus,
    frame: outputFrame,
    forceN,
    rawForceWorldN,
    filtered: booleanValue(signal.filtered, "signal.filtered"),
    deadbanded: booleanValue(signal.deadbanded, "signal.deadbanded"),
    rateLimited: booleanValue(signal.rate_limited, "signal.rate_limited"),
    clamped: booleanValue(signal.saturated, "signal.saturated"),
    reason: nullableString(signal.reason, "derived force reason"),
  };
}

function parseJsonLineStrict(text: string): ParsedJsonLine {
  let offset = 0;
  const rawTopLevelValues = new Map<string, string>();

  const fail = (): never => {
    throw new Error("contact JSONL line is malformed or non-canonical");
  };

  const parseString = (): string => {
    if (text[offset] !== '"') {
      return fail();
    }
    const start = offset;
    offset += 1;
    while (offset < text.length) {
      const code = text.charCodeAt(offset);
      const character = text[offset];
      if (character === '"') {
        offset += 1;
        const raw = text.slice(start, offset);
        let parsed: unknown;
        try {
          parsed = JSON.parse(raw);
        } catch {
          return fail();
        }
        if (typeof parsed !== "string") {
          return fail();
        }
        return parsed;
      }
      if (code < 0x20) {
        return fail();
      }
      if (character === "\\") {
        offset += 1;
        if (offset >= text.length) {
          return fail();
        }
      }
      offset += 1;
    }
    return fail();
  };

  const parseValue = (topLevel: boolean): unknown => {
    const character = text[offset];
    if (character === "{") {
      offset += 1;
      const result: JsonRecord = {};
      const keys = new Set<string>();
      let previousKey: string | null = null;
      if (text[offset] === "}") {
        offset += 1;
        return result;
      }
      while (offset < text.length) {
        const key = parseString();
        if (keys.has(key) || (previousKey !== null && key <= previousKey)) {
          return fail();
        }
        keys.add(key);
        previousKey = key;
        if (text[offset] !== ":") {
          return fail();
        }
        offset += 1;
        const rawStart = offset;
        result[key] = parseValue(false);
        if (topLevel) {
          rawTopLevelValues.set(key, text.slice(rawStart, offset));
        }
        if (text[offset] === "}") {
          offset += 1;
          return result;
        }
        if (text[offset] !== ",") {
          return fail();
        }
        offset += 1;
      }
      return fail();
    }
    if (character === "[") {
      offset += 1;
      const result: unknown[] = [];
      if (text[offset] === "]") {
        offset += 1;
        return result;
      }
      while (offset < text.length) {
        result.push(parseValue(false));
        if (text[offset] === "]") {
          offset += 1;
          return result;
        }
        if (text[offset] !== ",") {
          return fail();
        }
        offset += 1;
      }
      return fail();
    }
    if (character === '"') {
      return parseString();
    }
    if (text.startsWith("true", offset)) {
      offset += 4;
      return true;
    }
    if (text.startsWith("false", offset)) {
      offset += 5;
      return false;
    }
    if (text.startsWith("null", offset)) {
      offset += 4;
      return null;
    }
    const numberMatch = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(
      text.slice(offset),
    );
    if (numberMatch === null) {
      return fail();
    }
    const value = Number(numberMatch[0]);
    if (!Number.isFinite(value)) {
      return fail();
    }
    offset += numberMatch[0].length;
    return value;
  };

  const parsed = parseValue(true);
  if (offset !== text.length) {
    return fail();
  }
  return {
    value: record(parsed, "contact JSONL record"),
    rawTopLevelValues,
  };
}

async function digestCanonicalValue(raw: string): Promise<string> {
  if (typeof globalThis.crypto === "undefined" || globalThis.crypto.subtle === undefined) {
    throw new Error("Web Crypto is unavailable for contact manifest verification");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw));
  const hex = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return "sha256:" + hex;
}

function profileMismatch(
  binding: ContactTaskLogBinding,
  expectedProfile?: ContactTaskRobotProfileIdentity,
): boolean {
  return expectedProfile !== undefined && (
    binding.robot_bundle.plugin_id !== expectedProfile.profileId ||
    binding.robot_bundle.contract_version !== expectedProfile.profileContractVersion
  );
}

function parseTaskPhase(value: unknown, label: string): ContactTaskPhase {
  const phase = stringValue(value, label);
  if (!(CONTACT_TASK_PHASES as readonly string[]).includes(phase)) {
    throw new Error(label + " is unsupported");
  }
  return phase as ContactTaskPhase;
}

function parseTaskClassification(value: unknown, label: string): ContactTaskClassification {
  const classification = stringValue(value, label);
  if (!(CONTACT_TASK_CLASSIFICATIONS as readonly string[]).includes(classification)) {
    throw new Error(label + " is unsupported");
  }
  return classification as ContactTaskClassification;
}

function validateTaskLifecycle(
  phase: ContactTaskPhase,
  classification: ContactTaskClassification,
  reason: string | null,
  label: string,
): void {
  if (reason !== null && reason.trim().length === 0) {
    throw new Error(label + " reason must be non-empty or null");
  }
  if (classification === "success") {
    if (phase !== "success" || reason !== null) {
      throw new Error(label + " success state is inconsistent");
    }
  } else if (classification === "failure") {
    if (phase !== "failure" || reason === null) {
      throw new Error(label + " failure state is inconsistent");
    }
  } else if (classification === "technical_invalid") {
    if (phase !== "technical_invalid" || reason === null) {
      throw new Error(label + " technical-invalid state is inconsistent");
    }
  } else if (phase === "success" || phase === "failure" || phase === "technical_invalid") {
    throw new Error(label + " running state has a terminal phase");
  }
}

function validateTaskContext(value: unknown, binding: ContactTaskLogBinding): void {
  const context = exactKeys(
    value,
    [
      "approach_alignment_min_cosine",
      "dwell_interval_s",
      "max_contact_location_drift_m",
      "normal_alignment_min_cosine",
      "require_pose_measurement",
      "target_normal_force_band_n",
      "timeout_s",
      "trial",
    ],
    "contact task context",
  );
  if (!sameJson(parseTrial(context.trial), binding.trial)) {
    throw new Error("contact task trial does not match the log binding");
  }
  nonNegativeNumber(context.dwell_interval_s, "task_context.dwell_interval_s");
  nonNegativeNumber(context.timeout_s, "task_context.timeout_s");
  booleanValue(context.require_pose_measurement, "task_context.require_pose_measurement");
  if (context.target_normal_force_band_n === null) {
    return;
  }
  if (!Array.isArray(context.target_normal_force_band_n) || context.target_normal_force_band_n.length !== 2) {
    throw new Error("task context target force band is invalid");
  }
  context.target_normal_force_band_n.forEach((item, index) =>
    nonNegativeNumber(item, "task_context.target_normal_force_band_n[" + index + "]"),
  );
}

function validateTaskState(value: unknown): ParsedTaskState {
  const state = exactKeys(value, ["classification", "phase", "reason"], "contact task state");
  const phase = parseTaskPhase(state.phase, "task_state.phase");
  const classification = parseTaskClassification(state.classification, "task_state.classification");
  const reason = nullableString(state.reason, "task_state.reason");
  validateTaskLifecycle(phase, classification, reason, "task state");
  return { phase, classification, reason };
}

function validateTaskObservation(value: unknown): JsonRecord {
  const observation = exactKeys(
    value,
    [
      "contact_location_world_m",
      "object_orientation_wxyz",
      "object_position_world_m",
      "operator_status",
      "reason",
      "tip_position_world_m",
    ],
    "contact task observation",
  );
  for (const field of ["contact_location_world_m", "object_position_world_m", "tip_position_world_m"] as const) {
    if (observation[field] !== null) {
      vector3(observation[field], "task_observation." + field);
    }
  }
  if (observation.object_orientation_wxyz !== null) {
    quaternionWXYZ(observation.object_orientation_wxyz, "task_observation.object_orientation_wxyz");
  }
  stringValue(observation.operator_status, "task_observation.operator_status");
  nullableString(observation.reason, "task_observation.reason");
  return observation;
}

function validateOutcome(value: unknown, binding: ContactTaskLogBinding, sampleCount: number): JsonRecord {
  const outcome = exactKeys(
    value,
    [
      "approach_alignment_min_cosine",
      "classification",
      "completion_time_s",
      "contact_location_drift_m",
      "contact_loss_count",
      "dwell_interval_s",
      "final_contact_location_world_m",
      "final_normal_alignment_cosine",
      "final_object_orientation_wxyz",
      "final_object_position_world_m",
      "final_tip_position_world_m",
      "first_contact_time_s",
      "force_variability_n",
      "manifest_digest",
      "max_contact_location_drift_m",
      "max_penetration_m",
      "normal_alignment_min_cosine",
      "observations_count",
      "overshoot_m",
      "peak_normal_force_n",
      "peak_tangential_force_n",
      "phase",
      "reason",
      "recontact_count",
      "require_pose_measurement",
      "schema_version",
      "slip_proxy_m",
      "steady_state_error_m",
      "target_normal_force_band_n",
      "target_penetration_band_m",
      "terminal_time_s",
      "timeout_s",
      "trial",
    ],
    "contact task outcome",
  );
  if (
    outcome.schema_version !== OUTCOME_SCHEMA_VERSION ||
    outcome.manifest_digest !== binding.manifest_digest ||
    !sameJson(parseTrial(outcome.trial), binding.trial) ||
    nonNegativeInteger(outcome.observations_count, "outcome.observations_count") !== sampleCount
  ) {
    throw new Error("contact task outcome identity or sample count does not match the log");
  }
  const phase = parseTaskPhase(outcome.phase, "outcome.phase");
  const classification = parseTaskClassification(outcome.classification, "outcome.classification");
  const reason = nullableString(outcome.reason, "outcome.reason");
  validateTaskLifecycle(phase, classification, reason, "task outcome");
  const completionTimeS = outcome.completion_time_s === null
    ? null
    : nonNegativeNumber(outcome.completion_time_s, "outcome.completion_time_s");
  if (
    (classification === "success" && completionTimeS === null) ||
    (classification !== "success" && completionTimeS !== null)
  ) {
    throw new Error("contact task outcome completion time does not match its classification");
  }
  return outcome;
}

function validateFinalSampleOutcome(
  taskState: ParsedTaskState,
  rawEvidence: Pick<ParsedRawEvidence, "status" | "targetContacts">,
  phase: ContactTaskPhase,
  classification: ContactTaskClassification,
  reason: string | null,
): void {
  if (classification === "success") {
    if (
      taskState.phase !== "success" ||
      taskState.classification !== "success" ||
      taskState.reason !== null
    ) {
      throw new Error("successful outcome does not match the final task state");
    }
    if (rawEvidence.status !== "measured" || rawEvidence.targetContacts.length === 0) {
      throw new Error("successful outcome requires measured final target contact evidence");
    }
    return;
  }
  if (taskState.classification === "running" && classification === "failure") {
    return;
  }
  if (
    taskState.phase !== phase ||
    taskState.classification !== classification ||
    taskState.reason !== reason
  ) {
    throw new Error("task outcome does not match the final task state");
  }
}

function validateSample(
  value: unknown,
  expectedIndex: number,
  binding: ContactTaskLogBinding,
  signalManifest: ParsedSignalManifest,
): {
  document: JsonRecord;
  rawEvidence: ParsedRawEvidence;
  derivedForce: ParsedDerivedForce;
  observation: JsonRecord;
  taskState: ParsedTaskState;
} {
  const sample = exactKeys(
    value,
    [
      "binding",
      "derived_reaction_force",
      "elapsed_time_s",
      "raw_contact_evidence",
      "record_kind",
      "schema_version",
      "sequence_index",
      "task_observation",
      "task_state",
    ],
    "contact task log sample",
  );
  if (
    sample.record_kind !== "sample" ||
    sample.schema_version !== LOG_SCHEMA_VERSION ||
    nonNegativeInteger(sample.sequence_index, "sample.sequence_index") !== expectedIndex ||
    !sameJson(parseBinding(sample.binding), binding)
  ) {
    throw new Error("contact task log sample order or binding is invalid");
  }
  nonNegativeNumber(sample.elapsed_time_s, "sample.elapsed_time_s");
  const rawEvidence = parseRawEvidence(sample.raw_contact_evidence, binding);
  const derivedForce = parseDerivedForce(
    sample.derived_reaction_force,
    binding,
    signalManifest,
    rawEvidence,
  );
  const observation = validateTaskObservation(sample.task_observation);
  const taskState = validateTaskState(sample.task_state);
  return { document: sample, rawEvidence, derivedForce, observation, taskState };
}

function buildPresentationDocument(
  sample: ReturnType<typeof validateSample>,
  manifest: ParsedManifest,
  signalManifest: ParsedSignalManifest,
  binding: ContactTaskLogBinding,
  outcome: JsonRecord,
  sequenceIndex: number,
): JsonRecord {
  const rawEvidence = sample.rawEvidence;
  const derivedForce = sample.derivedForce;
  const objectPosition = sample.observation.object_position_world_m;
  const objectOrientation = sample.observation.object_orientation_wxyz;
  let status: ContactTaskPresentationStatus = "available";
  let reason: string | null = null;
  if (derivedForce.status === "stale") {
    status = "stale";
    reason = derivedForce.reason ?? "derived reaction-force signal is stale";
  } else if (rawEvidence.status !== "measured" && rawEvidence.status !== "no_contact") {
    status = "unavailable";
    reason = rawEvidence.reason ?? "raw contact evidence is unavailable";
  } else if (derivedForce.status !== "active" && derivedForce.status !== "no_contact") {
    status = "unavailable";
    reason = derivedForce.reason ?? "derived reaction-force signal is unavailable";
  } else if (objectPosition === null || objectOrientation === null) {
    status = "unavailable";
    reason = "backend object pose is unavailable";
  }
  return {
    schema_version: PRESENTATION_SCHEMA_VERSION,
    provenance: LOG_PROVENANCE,
    source_kind: binding.source_kind,
    evidence_notice: binding.source_kind === "synthetic_fixture" ? SYNTHETIC_NOTICE : null,
    status,
    reason,
    binding,
    sequence_index: sequenceIndex,
    payload_age_s: 0,
    max_age_s: signalManifest.maxInterSampleGapS,
    sample: {
      elapsed_time_s: sample.document.elapsed_time_s,
      sample_time_s: rawEvidence.sampleTimeS,
      simulation_time_s: rawEvidence.simulationTimeS,
      frame_index: rawEvidence.frameIndex,
    },
    cube: {
      identity: manifest.cube.identity,
      presentation_identity: manifest.presentationIdentity,
      shape: manifest.cube.shape,
      half_size_m: manifest.cube.halfSizeM,
      rgba: manifest.cube.rgba,
      position_world_m: objectPosition,
      orientation_wxyz: objectOrientation,
    },
    contacts: rawEvidence.targetContacts.map((contact) => ({
      contact_identity: contact.contactIdentity,
      normal_world: contact.normalWorld,
      penetration_m: contact.penetrationM,
      point_world_m: contact.pointWorldM,
    })),
    raw_evidence: {
      status: rawEvidence.status,
      reason: rawEvidence.reason,
      contact_count: rawEvidence.contactCount,
      force_world_n: rawEvidence.forceWorldN,
    },
    derived_force: {
      status: derivedForce.status,
      source_status: derivedForce.sourceStatus,
      frame: derivedForce.frame,
      force_n: derivedForce.forceN,
      raw_force_world_n: derivedForce.rawForceWorldN,
      unit: "newton",
      sign_convention: "object_on_tool",
      filtered: derivedForce.filtered,
      deadbanded: derivedForce.deadbanded,
      rate_limited: derivedForce.rateLimited,
      clamped: derivedForce.clamped,
      reason: derivedForce.reason,
    },
    task_state: sample.taskState,
    outcome: {
      phase: outcome.phase,
      classification: outcome.classification,
      reason: outcome.reason,
      completion_time_s: outcome.completion_time_s,
      observations_count: outcome.observations_count,
    },
  };
}

function parsePresentationDocument(
  value: unknown,
  expectedProfile?: ContactTaskRobotProfileIdentity,
  payloadContext?: ContactTaskPayloadContext,
): ContactTaskPresentationV1 {
  const presentation = exactKeys(
    value,
    [
      "binding",
      "contacts",
      "cube",
      "derived_force",
      "evidence_notice",
      "max_age_s",
      "outcome",
      "payload_age_s",
      "provenance",
      "raw_evidence",
      "reason",
      "sample",
      "schema_version",
      "sequence_index",
      "source_kind",
      "status",
      "task_state",
    ],
    "contact task presentation",
  );
  if (
    presentation.schema_version !== PRESENTATION_SCHEMA_VERSION ||
    presentation.provenance !== LOG_PROVENANCE
  ) {
    throw new Error("contact task presentation version or provenance is unsupported");
  }
  const sourceKind = parseSourceKind(presentation.source_kind);
  const expectedNotice = sourceKind === "synthetic_fixture" ? SYNTHETIC_NOTICE : null;
  if (presentation.evidence_notice !== expectedNotice) {
    throw new Error("contact task evidence notice does not match its declared source kind");
  }
  const binding = parseBinding(presentation.binding);
  if (profileMismatch(binding, expectedProfile)) {
    throw new Error("contact log robot bundle does not match the loaded viewer profile");
  }
  if (
    binding.scene_identity.name !== "contact_cube_scene" ||
    binding.scene_identity.version !== 1 ||
    binding.object_identity.name !== "contact_cube" ||
    binding.object_identity.version !== 1 ||
    binding.presentation_identity !== "contact-cube/v1"
  ) {
    throw new Error("contact presentation identity is unsupported");
  }
  const sequenceIndex = nonNegativeInteger(presentation.sequence_index, "presentation.sequence_index");
  const declaredPayloadAgeS = nonNegativeNumber(presentation.payload_age_s, "presentation.payload_age_s");
  let payloadAgeS = declaredPayloadAgeS;
  const maxAgeS = finiteNumber(presentation.max_age_s, "presentation.max_age_s");
  if (maxAgeS <= 0) {
    throw new Error("contact presentation maximum age must be positive");
  }
  const sample = exactKeys(
    presentation.sample,
    ["elapsed_time_s", "frame_index", "sample_time_s", "simulation_time_s"],
    "contact presentation sample",
  );
  const sampleFrameIndex = sample.frame_index === null
    ? null
    : nonNegativeInteger(sample.frame_index, "presentation.sample.frame_index");
  const parsedSample = {
    elapsedTimeS: nonNegativeNumber(sample.elapsed_time_s, "presentation.sample.elapsed_time_s"),
    sampleTimeS: nonNegativeNumber(sample.sample_time_s, "presentation.sample.sample_time_s"),
    simulationTimeS: nonNegativeNumber(sample.simulation_time_s, "presentation.sample.simulation_time_s"),
    frameIndex: sampleFrameIndex,
  };
  let contextStatus: ContactTaskPresentationStatus | null = null;
  let contextReason: string | null = null;
  if (payloadContext !== undefined) {
    const payloadTimeS = nonNegativeNumber(payloadContext.timeS, "outer payload time_s");
    const payloadFrameIndex = nonNegativeInteger(payloadContext.frameIndex, "outer payload frame_index");
    const computedAgeS = payloadTimeS - parsedSample.simulationTimeS;
    if (computedAgeS < 0) {
      payloadAgeS = 0;
      contextStatus = "unavailable";
      contextReason = "contact sample is newer than the outer payload state";
    } else {
      payloadAgeS = Math.max(declaredPayloadAgeS, computedAgeS);
    }
    if (sampleFrameIndex !== null && payloadFrameIndex < sampleFrameIndex) {
      contextStatus = "stale";
      contextReason = "contact sample frame is newer than the outer payload frame";
    }
  }
  const cubeValue = exactKeys(
    presentation.cube,
    [
      "half_size_m",
      "identity",
      "orientation_wxyz",
      "position_world_m",
      "presentation_identity",
      "rgba",
      "shape",
    ],
    "contact presentation cube",
  );
  const cubeIdentity = identity(cubeValue.identity, "presentation.cube.identity");
  const cubePosition = vector3(cubeValue.position_world_m, "presentation.cube.position_world_m");
  const cubeOrientation = quaternionWXYZ(cubeValue.orientation_wxyz, "presentation.cube.orientation_wxyz");
  const halfSizeM = vector3(cubeValue.half_size_m, "presentation.cube.half_size_m");
  if (
    !sameJson(cubeIdentity, binding.object_identity) ||
    cubeValue.presentation_identity !== binding.presentation_identity ||
    cubeValue.shape !== "box" ||
    halfSizeM.some((size) => size <= 0) ||
    !Array.isArray(cubeValue.rgba) ||
    cubeValue.rgba.length !== 4
  ) {
    throw new Error("contact cube presentation does not match its binding");
  }
  const rgba: [number, number, number, number] = [
    finiteNumber(cubeValue.rgba[0], "presentation.cube.rgba[0]"),
    finiteNumber(cubeValue.rgba[1], "presentation.cube.rgba[1]"),
    finiteNumber(cubeValue.rgba[2], "presentation.cube.rgba[2]"),
    finiteNumber(cubeValue.rgba[3], "presentation.cube.rgba[3]"),
  ];
  if (rgba.some((channel) => channel < 0 || channel > 1)) {
    throw new Error("contact cube presentation rgba is out of range");
  }
  if (!Array.isArray(presentation.contacts)) {
    throw new Error("contact presentation contacts must be an array");
  }
  const contacts = presentation.contacts.map((item, index) => {
    const contact = exactKeys(
      item,
      ["contact_identity", "normal_world", "penetration_m", "point_world_m"],
      "contact presentation record " + index,
    );
    const normalWorld = vector3(contact.normal_world, "contact presentation normal_world");
    const normalLength = Math.hypot(...normalWorld);
    if (normalLength < 1e-12 || Math.abs(normalLength - 1) > 1e-5) {
      throw new Error("contact presentation normal must be a unit vector");
    }
    return {
      contactIdentity: stringValue(contact.contact_identity, "contact presentation contact_identity"),
      pointWorldM: vector3(contact.point_world_m, "contact presentation point_world_m"),
      normalWorld,
      penetrationM: nonNegativeNumber(contact.penetration_m, "contact presentation penetration_m"),
    };
  });
  const rawValue = exactKeys(
    presentation.raw_evidence,
    ["contact_count", "force_world_n", "reason", "status"],
    "contact presentation raw evidence",
  );
  const rawStatus = stringValue(rawValue.status, "presentation.raw_evidence.status");
  const rawContactCount = rawValue.contact_count === null
    ? null
    : nonNegativeInteger(rawValue.contact_count, "presentation.raw_evidence.contact_count");
  const rawForce = rawValue.force_world_n === null
    ? null
    : vector3(rawValue.force_world_n, "presentation.raw_evidence.force_world_n");
  if (rawStatus === "measured" && (rawContactCount === null || rawContactCount < 1 || rawForce === null)) {
    throw new Error("measured presentation evidence must contain contacts and a raw force");
  }
  if (rawStatus === "no_contact" && (
    rawContactCount !== 0 || rawForce === null || rawForce.some((component) => component !== 0)
  )) {
    throw new Error("no-contact presentation evidence must contain an explicit zero");
  }
  if (rawStatus === "measured" && rawContactCount !== contacts.length) {
    throw new Error("presentation contact count does not match target contacts");
  }
  const derivedValue = exactKeys(
    presentation.derived_force,
    [
      "clamped",
      "deadbanded",
      "filtered",
      "force_n",
      "frame",
      "rate_limited",
      "raw_force_world_n",
      "reason",
      "sign_convention",
      "source_status",
      "status",
      "unit",
    ],
    "contact presentation derived force",
  );
  const derivedStatus = stringValue(derivedValue.status, "presentation.derived_force.status");
  const derivedFrameValue = derivedValue.frame;
  if (derivedFrameValue !== "mujoco_world" && derivedFrameValue !== "tool") {
    throw new Error("presentation derived force frame is unsupported");
  }
  const derivedFrame = derivedFrameValue as "mujoco_world" | "tool";
  if (derivedValue.unit !== "newton" || derivedValue.sign_convention !== "object_on_tool") {
    throw new Error("presentation derived force units or sign are unsupported");
  }
  const derivedForceN = derivedValue.force_n === null
    ? null
    : vector3(derivedValue.force_n, "presentation.derived_force.force_n");
  const derivedRawWorldN = derivedValue.raw_force_world_n === null
    ? null
    : vector3(derivedValue.raw_force_world_n, "presentation.derived_force.raw_force_world_n");
  const derivedSourceStatus = nullableString(
    derivedValue.source_status,
    "presentation.derived_force.source_status",
  );
  if (derivedStatus === "active") {
    if (
      rawStatus !== "measured" ||
      derivedSourceStatus !== "measured" ||
      derivedForceN === null ||
      rawForce === null ||
      derivedRawWorldN === null ||
      derivedRawWorldN.some((component, index) => component !== rawForce[index])
    ) {
      throw new Error("active derived force does not preserve raw measured contact evidence");
    }
  } else if (derivedStatus === "no_contact") {
    if (
      rawStatus !== "no_contact" ||
      derivedSourceStatus !== "no_contact" ||
      derivedForceN === null ||
      derivedForceN.some((component) => component !== 0) ||
      derivedRawWorldN === null ||
      derivedRawWorldN.some((component) => component !== 0)
    ) {
      throw new Error("no-contact derived force must remain an explicit zero");
    }
  } else if (derivedForceN !== null) {
    throw new Error("invalid derived force presentation must not carry a display force");
  }
  const parsedDerived = {
    status: derivedStatus,
    sourceStatus: derivedSourceStatus,
    frame: derivedFrame,
    forceN: derivedForceN,
    rawForceWorldN: derivedRawWorldN,
    filtered: booleanValue(derivedValue.filtered, "presentation.derived_force.filtered"),
    deadbanded: booleanValue(derivedValue.deadbanded, "presentation.derived_force.deadbanded"),
    rateLimited: booleanValue(derivedValue.rate_limited, "presentation.derived_force.rate_limited"),
    clamped: booleanValue(derivedValue.clamped, "presentation.derived_force.clamped"),
    reason: nullableString(derivedValue.reason, "presentation.derived_force.reason"),
  };
  const declaredStatus = stringValue(presentation.status, "contact presentation status");
  if (declaredStatus !== "available" && declaredStatus !== "unavailable" && declaredStatus !== "stale") {
    throw new Error("contact presentation status is unsupported");
  }
  let status: ContactTaskPresentationStatus = declaredStatus;
  let reason = nullableString(presentation.reason, "presentation.reason");
  if (contextStatus === "stale" || payloadAgeS > maxAgeS || derivedStatus === "stale") {
    status = "stale";
    reason = reason ?? contextReason ?? parsedDerived.reason ?? "contact sample exceeds the configured age boundary";
  } else if (contextStatus === "unavailable") {
    status = "unavailable";
    reason = reason ?? contextReason;
  } else if (
    rawStatus !== "measured" && rawStatus !== "no_contact"
  ) {
    status = "unavailable";
    reason = reason ?? nullableString(rawValue.reason, "presentation.raw_evidence.reason") ?? "raw contact evidence is unavailable";
  } else if (derivedStatus !== "active" && derivedStatus !== "no_contact") {
    status = "unavailable";
    reason = reason ?? parsedDerived.reason ?? "derived reaction-force signal is unavailable";
  }
  const taskState = validateTaskState(presentation.task_state);
  const outcomeValue = exactKeys(
    presentation.outcome,
    ["classification", "completion_time_s", "observations_count", "phase", "reason"],
    "contact presentation outcome",
  );
  const outcomePhase = parseTaskPhase(outcomeValue.phase, "presentation.outcome.phase");
  const outcomeClassification = parseTaskClassification(
    outcomeValue.classification,
    "presentation.outcome.classification",
  );
  const outcomeReason = nullableString(outcomeValue.reason, "presentation.outcome.reason");
  validateTaskLifecycle(outcomePhase, outcomeClassification, outcomeReason, "presentation outcome");
  const completionTimeS = outcomeValue.completion_time_s === null
    ? null
    : nonNegativeNumber(outcomeValue.completion_time_s, "presentation.outcome.completion_time_s");
  if (
    (outcomeClassification === "success" && completionTimeS === null) ||
    (outcomeClassification !== "success" && completionTimeS !== null)
  ) {
    throw new Error("presentation outcome completion time does not match its classification");
  }
  const observationsCount = nonNegativeInteger(
    outcomeValue.observations_count,
    "presentation.outcome.observations_count",
  );
  validateFinalSampleOutcome(
    taskState,
    { status: rawStatus, targetContacts: contacts },
    outcomePhase,
    outcomeClassification,
    outcomeReason,
  );
  if (
    parsedDerived.frame !== "mujoco_world" &&
    parsedDerived.forceN !== null &&
    parsedDerived.forceN.some((component) => !Number.isFinite(component))
  ) {
    throw new Error("derived force contains a non-finite component");
  }
  return {
    status,
    reason,
    sourceKind,
    evidenceNotice: expectedNotice,
    binding,
    sequenceIndex,
    payloadAgeS,
    maxAgeS,
    sample: parsedSample,
    cube: {
      identity: cubeIdentity,
      presentationIdentity: binding.presentation_identity,
      shape: "box",
      halfSizeM,
      rgba,
      positionWorldM: cubePosition,
      orientationWXYZ: cubeOrientation,
    },
    contacts,
    rawEvidence: {
      status: rawStatus,
      reason: nullableString(rawValue.reason, "presentation.raw_evidence.reason"),
      contactCount: rawContactCount,
      forceWorldN: rawForce,
    },
    derivedForce: status === "available"
      ? {
          ...parsedDerived,
          forceN: parsedDerived.forceN,
          unit: "newton",
          signConvention: "object_on_tool",
        }
      : null,
    taskState: status === "available" ? taskState : null,
    outcome: status === "available"
      ? {
          phase: outcomePhase,
          classification: outcomeClassification,
          reason: outcomeReason,
          completionTimeS,
          observationsCount,
        }
      : null,
  };
}

/** versionedなpayload-v0 contact extensionをparseし、不一致はすべてunavailableとして返す。 */
export function parseContactTaskPresentationV1(
  value: unknown,
  expectedProfile?: ContactTaskRobotProfileIdentity,
  payloadContext?: ContactTaskPayloadContext,
): ContactTaskPresentationV1 {
  if (value === undefined || value === null) {
    return unavailableContactTaskPresentation("contact_task_v1 metadata がありません");
  }
  try {
    return parsePresentationDocument(value, expectedProfile, payloadContext);
  } catch (error) {
    return unavailableContactTaskPresentation(
      error instanceof Error ? error.message : "contact task presentation is invalid",
    );
  }
}

/** offline viewer表示用の完全なcontact-task-log/v1 JSONLを読む。 */
export async function parseContactTaskLogJsonl(
  text: string,
  expectedProfile?: ContactTaskRobotProfileIdentity,
): Promise<ContactTaskPresentationV1> {
  try {
    if (
      typeof text !== "string" ||
      text.length === 0 ||
      text.charCodeAt(0) === 0xfeff ||
      text.includes("\r") ||
      !text.endsWith("\n")
    ) {
      throw new Error("contact task log must be UTF-8 LF JSONL with a final newline");
    }
    const lines = text.slice(0, -1).split("\n");
    if (lines.length < 3 || lines.some((line) => line.length === 0)) {
      throw new Error("contact task log requires a header, samples, and summary");
    }
    const parsedLines = lines.map(parseJsonLineStrict);
    const headerLine = parsedLines[0];
    const header = exactKeys(
      headerLine.value,
      [
        "binding",
        "contract_version",
        "manifest",
        "provenance",
        "record_kind",
        "schema_version",
        "signal_manifest",
        "source_kind",
        "task_context",
      ],
      "contact task log header",
    );
    if (
      header.record_kind !== "header" ||
      header.schema_version !== LOG_SCHEMA_VERSION ||
      header.contract_version !== 1 ||
      header.provenance !== LOG_PROVENANCE
    ) {
      throw new Error("contact task log header version or provenance is unsupported");
    }
    const binding = parseBinding(header.binding);
    const sourceKind = parseSourceKind(header.source_kind);
    if (sourceKind !== binding.source_kind) {
      throw new Error("contact log source kind does not match its binding");
    }
    validateTaskContext(header.task_context, binding);
    const manifest = parseManifest(header.manifest, binding);
    const rawManifest = headerLine.rawTopLevelValues.get("manifest");
    const rawSignalManifest = headerLine.rawTopLevelValues.get("signal_manifest");
    if (rawManifest === undefined || rawSignalManifest === undefined) {
      throw new Error("contact task log header is missing canonical manifest bytes");
    }
    if (
      (await digestCanonicalValue(rawManifest)) !== binding.manifest_digest ||
      (await digestCanonicalValue(rawSignalManifest)) !== binding.signal_manifest_digest
    ) {
      throw new Error("contact task log manifest digest verification failed");
    }
    const signalManifest = parseSignalManifest(header.signal_manifest, binding);
    if (profileMismatch(binding, expectedProfile)) {
      throw new Error("contact log robot bundle does not match the loaded viewer profile");
    }

    const sampleLines = parsedLines.slice(1, -1);
    const samples = sampleLines.map((line, index) =>
      validateSample(line.value, index, binding, signalManifest),
    );
    const summary = exactKeys(
      parsedLines[parsedLines.length - 1].value,
      ["binding", "outcome", "record_kind", "sample_count", "schema_version"],
      "contact task log summary",
    );
    if (
      summary.record_kind !== "summary" ||
      summary.schema_version !== LOG_SCHEMA_VERSION ||
      nonNegativeInteger(summary.sample_count, "summary.sample_count") !== samples.length ||
      !sameJson(parseBinding(summary.binding), binding)
    ) {
      throw new Error("contact task log summary identity or sample count is invalid");
    }
    const outcome = validateOutcome(summary.outcome, binding, samples.length);
    const lastSample = samples[samples.length - 1];
    validateFinalSampleOutcome(
      lastSample.taskState,
      lastSample.rawEvidence,
      parseTaskPhase(outcome.phase, "outcome.phase"),
      parseTaskClassification(outcome.classification, "outcome.classification"),
      nullableString(outcome.reason, "outcome.reason"),
    );
    const projection = buildPresentationDocument(
      lastSample,
      manifest,
      signalManifest,
      binding,
      outcome,
      samples.length - 1,
    );
    return parsePresentationDocument(projection, expectedProfile);
  } catch (error) {
    return unavailableContactTaskPresentation(
      error instanceof Error ? error.message : "contact task log is invalid",
    );
  }
}
