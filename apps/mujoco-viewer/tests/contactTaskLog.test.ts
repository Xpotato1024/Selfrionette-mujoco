import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { parseContactTaskLogJsonl, parseContactTaskPresentationV1, type ContactTaskPresentationV1 } from "../src/contact/contactTaskLog.js";

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
