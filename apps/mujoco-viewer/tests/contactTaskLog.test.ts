import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parseContactTaskLogJsonl, parseContactTaskPresentationV1, type ContactTaskPresentationV1 } from "../src/contact/contactTaskLog.js";
import { resolveTransportQpos } from "../src/wasm-scene/mujocoQposSync.js";
import type { TransportPayloadV0 } from "../src/types/transportPayload.js";
import { FAST_ARM_VIEWER_PROFILE } from "./testViewerProfile.js";

const expectedProfile = { profileId: "fast_arm", profileContractVersion: 1 };
const fixturePath = join(
  process.cwd(),
  "tests",
  "fixtures",
  "contact-cube-v1-demo.jsonl",
);
const fixture = await readFile(fixturePath, "utf8");

const available = await parseContactTaskLogJsonl(fixture, expectedProfile);
assert.equal(available.status, "available");
assert.equal(available.sourceKind, "synthetic_fixture");
assert.match(available.evidenceNotice ?? "", /MuJoCoから取得した接触証拠ではありません/);
assert.deepEqual(available.rawEvidence?.forceWorldN, [2, 0, 0]);
assert.deepEqual(available.derivedForce?.forceN, [2, 0, 0]);
assert.equal(available.derivedForce?.frame, "mujoco_world");
assert.equal(available.outcome?.classification, "success");
assert.deepEqual(available.cube?.halfSizeM, [0.04, 0.04, 0.04]);
assert.deepEqual(available.contacts[0]?.pointWorldM, [0.19, 0, 0.07]);

const wirePresentation = toWirePresentation(available);
const sample = available.sample!;
const sampleFrameIndex = sample.frameIndex ?? 0;
const freshOuter = parseContactTaskPresentationV1(wirePresentation, expectedProfile, {
  timeS: sample.simulationTimeS + 0.01,
  frameIndex: sampleFrameIndex + 1,
});
assert.equal(freshOuter.status, "available");
assert.ok(Math.abs((freshOuter.payloadAgeS ?? -1) - 0.01) < 1e-9);

const reusedMetadataOuter = parseContactTaskPresentationV1(
  wirePresentation,
  expectedProfile,
  {
    timeS: sample.simulationTimeS + (available.maxAgeS ?? 0) + 0.01,
    frameIndex: sampleFrameIndex + 2,
  },
);
assert.equal(reusedMetadataOuter.status, "stale");
assert.ok((reusedMetadataOuter.payloadAgeS ?? 0) > (reusedMetadataOuter.maxAgeS ?? 0));
assert.equal(reusedMetadataOuter.derivedForce, null);
assert.equal(reusedMetadataOuter.taskState, null);
assert.equal(reusedMetadataOuter.outcome, null);
assert.deepEqual(reusedMetadataOuter.rawEvidence?.forceWorldN, [2, 0, 0]);

const futureEvidenceOuter = parseContactTaskPresentationV1(
  wirePresentation,
  expectedProfile,
  {
    timeS: sample.simulationTimeS - 0.01,
    frameIndex: sampleFrameIndex,
  },
);
assert.equal(futureEvidenceOuter.status, "unavailable");
assert.equal(futureEvidenceOuter.derivedForce, null);
assert.equal(futureEvidenceOuter.taskState, null);
assert.equal(futureEvidenceOuter.outcome, null);

function contactSceneRobotQposProjection(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    schema_version: "contact-scene-robot-qpos/v1",
    scene_identity: available.binding!.scene_identity,
    manifest_digest: available.binding!.manifest_digest,
    frame_index: sampleFrameIndex,
    time_s: sample.simulationTimeS,
    source_qpos_dimension: 11,
    robot_profile_id: FAST_ARM_VIEWER_PROFILE.profileId,
    model_contract_version: FAST_ARM_VIEWER_PROFILE.modelContractVersion,
    robot_qpos_dimension: FAST_ARM_VIEWER_PROFILE.qposDimension,
    robot_joint_names: Array.from(FAST_ARM_VIEWER_PROFILE.jointNames),
    qpos_addresses: [0, 4, 6, 10],
    ...overrides,
  };
}

function payloadWithRobotQposProjection(
  projection: Record<string, unknown>,
  {
    contactTask = wirePresentation,
    frameIndex = sampleFrameIndex,
    timeS = sample.simulationTimeS,
    qpos = Array.from({ length: 11 }, (_, index) => index + 1),
  }: {
    contactTask?: unknown;
    frameIndex?: number;
    timeS?: number;
    qpos?: number[];
  } = {},
): TransportPayloadV0 {
  return {
    version: 0,
    frame_index: frameIndex,
    time_s: timeS,
    qpos,
    qvel: [],
    bodies: [],
    sites: [],
    target_position_m: null,
    metadata: {
      robot_profile_id: FAST_ARM_VIEWER_PROFILE.profileId,
      model_contract_version: FAST_ARM_VIEWER_PROFILE.modelContractVersion,
      robot_joint_names: Array.from(FAST_ARM_VIEWER_PROFILE.jointNames),
      robot_qpos_dimension: FAST_ARM_VIEWER_PROFILE.qposDimension,
      contact_task_v1: contactTask,
      contact_scene_robot_qpos_v1: projection,
    },
  };
}

const projectedQpos = resolveTransportQpos(
  payloadWithRobotQposProjection(contactSceneRobotQposProjection()),
  FAST_ARM_VIEWER_PROFILE.qposDimension,
  FAST_ARM_VIEWER_PROFILE,
);
assert.equal(projectedQpos.status, "ready", projectedQpos.errorMessage ?? undefined);
assert.deepEqual(projectedQpos.qpos, [1, 5, 7, 11]);

function assertInvalidProjection(
  payload: TransportPayloadV0,
  pattern: RegExp,
): void {
  const result = resolveTransportQpos(
    payload,
    FAST_ARM_VIEWER_PROFILE.qposDimension,
    FAST_ARM_VIEWER_PROFILE,
  );
  assert.equal(result.status, "invalid");
  assert.equal(result.qpos, null);
  assert.match(result.errorMessage ?? "", pattern);
}

const unknownProjectionField = contactSceneRobotQposProjection({ unexpected: true });
assertInvalidProjection(
  payloadWithRobotQposProjection(unknownProjectionField),
  /fields do not match/,
);
const missingAddressProjection = contactSceneRobotQposProjection();
delete missingAddressProjection.qpos_addresses;
assertInvalidProjection(
  payloadWithRobotQposProjection(missingAddressProjection),
  /fields do not match/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({
      manifest_digest: `sha256:${"0".repeat(64)}`,
    }),
  ),
  /does not match contact manifest binding/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({
      scene_identity: { name: "other_scene", version: 1 },
    }),
  ),
  /does not match contact manifest binding/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({ frame_index: sampleFrameIndex + 1 }),
  ),
  /does not match payload frame\/time/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({ time_s: sample.simulationTimeS + 0.001 }),
  ),
  /does not match payload frame\/time/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({ source_qpos_dimension: 12 }),
  ),
  /source qpos dimension/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({ robot_profile_id: "other_robot" }),
  ),
  /loaded Robot profile/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({
      robot_joint_names: ["wrong", ...Array.from(FAST_ARM_VIEWER_PROFILE.jointNames).slice(1)],
    }),
  ),
  /joint name\/order/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({ qpos_addresses: [0, 0, 6, 10] }),
  ),
  /qpos addresses/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({ qpos_addresses: [0, 4, 6, 11] }),
  ),
  /qpos addresses/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection(),
    { qpos: [1, 2, Number.NaN, 4, 5, 6, 7, 8, 9, 10, 11] },
  ),
  /source qpos dimension or values/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection(),
    { contactTask: null },
  ),
  /contact_task_v1 binding is missing/,
);
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({
      frame_index: sampleFrameIndex + 1,
      time_s: sample.simulationTimeS + 0.001,
    }),
    {
      frameIndex: sampleFrameIndex + 1,
      timeS: sample.simulationTimeS + 0.001,
    },
  ),
  /sample was replayed or does not match payload frame\/time/,
);
const staleOuterTime = sample.simulationTimeS + (available.maxAgeS ?? 0) + 0.01;
assertInvalidProjection(
  payloadWithRobotQposProjection(
    contactSceneRobotQposProjection({
      frame_index: sampleFrameIndex + 2,
      time_s: staleOuterTime,
    }),
    {
      frameIndex: sampleFrameIndex + 2,
      timeS: staleOuterTime,
    },
  ),
  /contact_task_v1 binding is missing, stale, or unavailable/,
);

const mismatchedProfile = await parseContactTaskLogJsonl(fixture, {
  profileId: "another_robot",
  profileContractVersion: 1,
});
assert.equal(mismatchedProfile.status, "unavailable");
assert.equal(mismatchedProfile.cube, null);
assert.equal(mismatchedProfile.derivedForce, null);

const malformed = await parseContactTaskLogJsonl(fixture.replace('"source_kind":"synthetic_fixture"', '"source_kind":"runtime_capture"'), expectedProfile);
assert.equal(malformed.status, "unavailable");
assert.equal(malformed.cube, null);
assert.equal(malformed.derivedForce, null);

const truncated = await parseContactTaskLogJsonl(fixture.slice(0, -1), expectedProfile);
assert.equal(truncated.status, "unavailable");
assert.equal(truncated.cube, null);
assert.equal(truncated.derivedForce, null);

const taskConditionMismatches: Array<[string, unknown]> = [
  ["dwell_interval_s", 0.3],
  ["timeout_s", 1.5],
  ["target_normal_force_band_n", [1.5, 3.5]],
  ["approach_alignment_min_cosine", 0.5],
  ["normal_alignment_min_cosine", 0.5],
  ["max_contact_location_drift_m", 0.01],
  ["require_pose_measurement", true],
];
for (const [field, mismatch] of taskConditionMismatches) {
  const lines = fixture.trimEnd().split("\n");
  const summary = JSON.parse(lines[lines.length - 1]!) as Record<string, unknown>;
  const outcome = summary["outcome"] as Record<string, unknown>;
  outcome[field] = mismatch;
  lines[lines.length - 1] = JSON.stringify(summary);
  const inconsistentConditions = lines.join("\n") + "\n";
  const rejectedConditions = await parseContactTaskLogJsonl(inconsistentConditions, expectedProfile);
  assert.equal(rejectedConditions.status, "unavailable", `outcome ${field} must match header context`);
  assert.equal(rejectedConditions.reason, "contact task outcome conditions do not match the header context");
}

const sourceLines = fixture.trimEnd().split("\n");
const signalManifestMatch = sourceLines[0]!.match(/"signal_manifest":(\{.*\}),"source_kind":/);
assert.ok(signalManifestMatch);
const deviceNeutralSignalManifest = signalManifestMatch[1]!.replace(
  '"output_frame":"mujoco_world"',
  '"output_frame":"device_neutral"',
);
const signalManifestDigest = "sha256:" + createHash("sha256").update(deviceNeutralSignalManifest).digest("hex");
const deviceNeutralHeader = sourceLines[0]!
  .replace(/"signal_manifest":\{.*\},"source_kind":/, `"signal_manifest":${deviceNeutralSignalManifest},"source_kind":`)
  .replace(/"signal_manifest_digest":"sha256:[0-9a-f]{64}"/, `"signal_manifest_digest":"${signalManifestDigest}"`);
const deviceNeutralLines = sourceLines.slice(1).map((line) => JSON.parse(line) as Record<string, unknown>);
for (const line of deviceNeutralLines) {
  const binding = line["binding"] as Record<string, unknown>;
  binding["signal_manifest_digest"] = signalManifestDigest;
}
for (const line of deviceNeutralLines) {
  if (line["record_kind"] !== "sample") {
    continue;
  }
  const derivedSignal = line["derived_reaction_force"] as Record<string, unknown>;
  derivedSignal["manifest_digest"] = signalManifestDigest;
  const derivedOutput = derivedSignal["output"] as Record<string, unknown>;
  derivedOutput["frame"] = "device_neutral";
}
const deviceNeutralLog = [deviceNeutralHeader, ...deviceNeutralLines.map((line) => JSON.stringify(line))].join("\n") + "\n";
const deviceNeutralPresentation = await parseContactTaskLogJsonl(deviceNeutralLog, expectedProfile);
assert.equal(deviceNeutralPresentation.status, "available", deviceNeutralPresentation.reason ?? "device-neutral presentation was unavailable");
assert.equal(deviceNeutralPresentation.derivedForce?.frame, "device_neutral");
assert.deepEqual(deviceNeutralPresentation.derivedForce?.forceN, [2, 0, 0]);
assert.notEqual(deviceNeutralPresentation.derivedForce?.frame, "mujoco_world");
assert.notEqual(deviceNeutralPresentation.derivedForce?.forceN, null);
const sceneRendererSource = await readFile(
  join(process.cwd(), "src", "wasm-scene", "mujocoSceneRenderer.ts"),
  "utf8",
);
assert.match(
  sceneRendererSource,
  /if\s*\(\s*presentation\.derivedForce\?\.frame === "mujoco_world"\s*&&\s*presentation\.derivedForce\.forceN !== null\s*\)\s*\{\s*arrow\(presentation\.derivedForce\.forceN,\s*forceOrigin,\s*0xfacc15\);/,
);

const invalidDerivedWire = toWirePresentation(available);
const invalidDerived = invalidDerivedWire["derived_force"] as Record<string, unknown>;
invalidDerived["status"] = "invalid";
invalidDerived["force_n"] = null;
const invalidDerivedPresentation = parseContactTaskPresentationV1(invalidDerivedWire, expectedProfile);
assert.equal(invalidDerivedPresentation.status, "unavailable");
assert.equal(invalidDerivedPresentation.derivedForce, null);
assert.equal(invalidDerivedPresentation.reason, "derived reaction-force signal is unavailable");

for (const rawStatus of ["invalid_contact", "solver_invalid"]) {
  const rawStatusAsDerivedWire = toWirePresentation(available);
  const derived = rawStatusAsDerivedWire["derived_force"] as Record<string, unknown>;
  derived["status"] = rawStatus;
  derived["force_n"] = null;
  const rejectedDerivedStatus = parseContactTaskPresentationV1(rawStatusAsDerivedWire, expectedProfile);
  assert.equal(rejectedDerivedStatus.status, "unavailable");
  assert.equal(rejectedDerivedStatus.derivedForce, null);
  assert.equal(rejectedDerivedStatus.reason, "presentation derived force status is unsupported");
}

const invalidSignalLines = fixture.trimEnd().split("\n");
for (let index = 1; index < invalidSignalLines.length - 1; index += 1) {
  const invalidSignalSample = JSON.parse(invalidSignalLines[index]!) as Record<string, unknown>;
  const invalidSignal = invalidSignalSample["derived_reaction_force"] as Record<string, unknown>;
  invalidSignal["status"] = "invalid";
  const invalidSignalOutput = invalidSignal["output"] as Record<string, unknown>;
  invalidSignalOutput["force_n"] = null;
  invalidSignalLines[index] = JSON.stringify(invalidSignalSample);
}
const invalidSignalLog = invalidSignalLines.join("\n") + "\n";
const invalidSignalPresentation = await parseContactTaskLogJsonl(invalidSignalLog, expectedProfile);
assert.equal(invalidSignalPresentation.status, "unavailable");
assert.equal(invalidSignalPresentation.derivedForce, null);
assert.equal(invalidSignalPresentation.reason, "derived reaction-force signal is unavailable");

for (const rawStatus of ["invalid_contact", "solver_invalid"]) {
  const rawStatusLines = fixture.trimEnd().split("\n");
  for (let index = 1; index < rawStatusLines.length - 1; index += 1) {
    const sampleLine = JSON.parse(rawStatusLines[index]!) as Record<string, unknown>;
    const signal = sampleLine["derived_reaction_force"] as Record<string, unknown>;
    signal["status"] = rawStatus;
    const output = signal["output"] as Record<string, unknown>;
    output["force_n"] = null;
    rawStatusLines[index] = JSON.stringify(sampleLine);
  }
  const rawStatusLog = rawStatusLines.join("\n") + "\n";
  const rejectedRawStatus = await parseContactTaskLogJsonl(rawStatusLog, expectedProfile);
  assert.equal(rejectedRawStatus.status, "unavailable");
  assert.equal(rejectedRawStatus.reason, "derived reaction-force status is unsupported");
}

function toWirePresentation(presentation: ContactTaskPresentationV1): Record<string, unknown> {
  const sample = presentation.sample!;
  const cube = presentation.cube!;
  const rawEvidence = presentation.rawEvidence!;
  const derivedForce = presentation.derivedForce!;
  const taskState = presentation.taskState!;
  const outcome = presentation.outcome!;
  return {
    schema_version: "contact-task-presentation/v1",
    provenance: "runtime_contact_task_log/v1",
    source_kind: presentation.sourceKind,
    evidence_notice: presentation.evidenceNotice,
    status: presentation.status,
    reason: presentation.reason,
    binding: presentation.binding,
    sequence_index: presentation.sequenceIndex,
    payload_age_s: presentation.payloadAgeS,
    max_age_s: presentation.maxAgeS,
    sample: {
      elapsed_time_s: sample.elapsedTimeS,
      sample_time_s: sample.sampleTimeS,
      simulation_time_s: sample.simulationTimeS,
      frame_index: sample.frameIndex,
    },
    cube: {
      identity: cube.identity,
      presentation_identity: cube.presentationIdentity,
      shape: cube.shape,
      half_size_m: cube.halfSizeM,
      rgba: cube.rgba,
      position_world_m: cube.positionWorldM,
      orientation_wxyz: cube.orientationWXYZ,
    },
    contacts: presentation.contacts.map((contact) => ({
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
      unit: derivedForce.unit,
      sign_convention: derivedForce.signConvention,
      filtered: derivedForce.filtered,
      deadbanded: derivedForce.deadbanded,
      rate_limited: derivedForce.rateLimited,
      clamped: derivedForce.clamped,
      reason: derivedForce.reason,
    },
    task_state: {
      phase: taskState.phase,
      classification: taskState.classification,
      reason: taskState.reason,
    },
    outcome: {
      phase: outcome.phase,
      classification: outcome.classification,
      reason: outcome.reason,
      completion_time_s: outcome.completionTimeS,
      observations_count: outcome.observationsCount,
    },
  };
}

type JsonDocument = Record<string, unknown>;

function objectValue(value: unknown): JsonDocument {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("expected JSON object in contact task log test");
  }
  return value as JsonDocument;
}

function editJsonl(source: string, update: (documents: JsonDocument[]) => void): string {
  const sourceLines = source.slice(0, -1).split("\n");
  const headerLine = sourceLines[0];
  if (headerLine === undefined) {
    throw new Error("contact log test fixture is empty");
  }
  const documents = sourceLines.map((line) => objectValue(JSON.parse(line)));
  update(documents);
  return [
    headerLine,
    ...documents.slice(1).map((document) => JSON.stringify(document)),
  ].join("\n") + "\n";
}

function noContactFinalizerLog(source: string): string {
  return editJsonl(source, (documents) => {
    const finalSample = objectValue(documents[documents.length - 2]);
    const evidence = objectValue(finalSample["raw_contact_evidence"]);
    evidence["aggregate"] = {
      contact_count: 0,
      normal_force_n: 0,
      object_on_tool_force_world_n: [0, 0, 0],
      object_on_tool_wrench_world_nm: [0, 0, 0, 0, 0, 0],
      resultant_force_n: 0,
      resultant_force_world_n: [0, 0, 0],
      tangential_force_world_n: [0, 0, 0],
      tool_on_object_force_world_n: [0, 0, 0],
    };
    evidence["contacts"] = [];
    evidence["reason"] = null;
    evidence["status"] = "no_contact";

    const signal = objectValue(finalSample["derived_reaction_force"]);
    objectValue(signal["force_source"])["status"] = "no_contact";
    const output = objectValue(signal["output"]);
    output["force_n"] = [0, 0, 0];
    output["raw_force_n"] = [0, 0, 0];
    signal["deadbanded"] = false;
    signal["filtered"] = false;
    signal["rate_limited"] = false;
    signal["raw_force_world_n"] = [0, 0, 0];
    signal["reason"] = null;
    signal["saturated"] = false;
    signal["status"] = "no_contact";

    const taskState = objectValue(finalSample["task_state"]);
    taskState["classification"] = "running";
    taskState["phase"] = "approach";
    taskState["reason"] = null;

    const summary = objectValue(documents[documents.length - 1]);
    const outcome = objectValue(summary["outcome"]);
    outcome["classification"] = "failure";
    outcome["completion_time_s"] = null;
    outcome["phase"] = "failure";
    outcome["reason"] = "contact task fixture ended before terminal classification";
  });
}

const noContactLog = noContactFinalizerLog(fixture);
const finalizedNoContact = await parseContactTaskLogJsonl(noContactLog, expectedProfile);
assert.equal(finalizedNoContact.status, "available");
assert.equal(finalizedNoContact.rawEvidence?.status, "no_contact");
assert.equal(finalizedNoContact.taskState?.classification, "running");
assert.equal(finalizedNoContact.outcome?.classification, "failure");

const forgedNoContactSuccessLog = editJsonl(noContactLog, (documents) => {
  const finalSample = objectValue(documents[documents.length - 2]);
  const taskState = objectValue(finalSample["task_state"]);
  taskState["classification"] = "success";
  taskState["phase"] = "success";
  taskState["reason"] = null;
  const summary = objectValue(documents[documents.length - 1]);
  const outcome = objectValue(summary["outcome"]);
  outcome["classification"] = "success";
  outcome["completion_time_s"] = 0.2;
  outcome["phase"] = "success";
  outcome["reason"] = null;
});
const forgedNoContactSuccess = await parseContactTaskLogJsonl(
  forgedNoContactSuccessLog,
  expectedProfile,
);
assert.equal(forgedNoContactSuccess.status, "unavailable");
assert.match(forgedNoContactSuccess.reason ?? "", /measured final target contact evidence/);

const mismatchedSummaryLog = editJsonl(fixture, (documents) => {
  const finalSample = objectValue(documents[documents.length - 2]);
  const taskState = objectValue(finalSample["task_state"]);
  taskState["classification"] = "failure";
  taskState["phase"] = "failure";
  taskState["reason"] = "synthetic final-state mismatch";
});
const mismatchedSummary = await parseContactTaskLogJsonl(mismatchedSummaryLog, expectedProfile);
assert.equal(mismatchedSummary.status, "unavailable");
assert.match(mismatchedSummary.reason ?? "", /does not match the final task state/);

const unknownPhaseLog = editJsonl(fixture, (documents) => {
  const finalSample = objectValue(documents[documents.length - 2]);
  objectValue(finalSample["task_state"])["phase"] = "unsupported_phase";
});
const unknownPhase = await parseContactTaskLogJsonl(unknownPhaseLog, expectedProfile);
assert.equal(unknownPhase.status, "unavailable");
assert.match(unknownPhase.reason ?? "", /task_state.phase is unsupported/);

const impreciseRawForceLog = editJsonl(fixture, (documents) => {
  const finalSample = objectValue(documents[documents.length - 2]);
  const signal = objectValue(finalSample["derived_reaction_force"]);
  const rawForce = signal["raw_force_world_n"] as number[];
  rawForce[0] = 2.0000005;
});
const impreciseRawForce = await parseContactTaskLogJsonl(impreciseRawForceLog, expectedProfile);
assert.equal(impreciseRawForce.status, "unavailable");
assert.match(impreciseRawForce.reason ?? "", /does not preserve the raw contact aggregate/);

const unboundedForceBandLog = fixture.replaceAll(
  '"target_normal_force_band_n":[1.0,3.0]',
  '"target_normal_force_band_n":null',
);
const unboundedForceBand = await parseContactTaskLogJsonl(unboundedForceBandLog, expectedProfile);
assert.equal(unboundedForceBand.status, "available");

const mismatchedMetadata = toWirePresentation(available);
const mismatchedMetadataState = objectValue(mismatchedMetadata["task_state"]);
mismatchedMetadataState["classification"] = "failure";
mismatchedMetadataState["phase"] = "failure";
mismatchedMetadataState["reason"] = "synthetic metadata mismatch";
const mismatchedMetadataResult = parseContactTaskPresentationV1(
  mismatchedMetadata,
  expectedProfile,
);
assert.equal(mismatchedMetadataResult.status, "unavailable");
assert.match(mismatchedMetadataResult.reason ?? "", /does not match the final task state/);

const impreciseMetadata = toWirePresentation(available);
objectValue(impreciseMetadata["derived_force"])["raw_force_world_n"] = [2.0000005, 0, 0];
const impreciseMetadataResult = parseContactTaskPresentationV1(
  impreciseMetadata,
  expectedProfile,
);
assert.equal(impreciseMetadataResult.status, "unavailable");
assert.match(impreciseMetadataResult.reason ?? "", /does not preserve raw measured contact evidence/);
console.log("contact-task-log viewer tests passed");
