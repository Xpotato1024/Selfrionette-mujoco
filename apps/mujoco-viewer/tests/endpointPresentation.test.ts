import assert from "node:assert/strict";
import { buildEndpointPresentationState, formatEndpointPresentationText } from "../src/wasm-scene/endpointPresentation.js";

const complete = buildEndpointPresentationState({
  desired_endpoint_m: [0.3, 0.4, 0.5], local_endpoint_velocity_m_s: [0.01, 0.02, 0.03],
  requested_control_frame: "tool", resolved_control_frame: "mujoco_world",
  control_frame_resolution_status: "tool_orientation_resolved",
  resolved_world_endpoint_velocity_m_s: [-0.02, 0.01, 0.03],
  endpoint_delta_requested_m: [-0.002, 0.001, 0.003], endpoint_delta_achieved_m: [-0.0018, 0.0009, 0.0027],
  actual_tip_delta_m: [-0.0017, 0.0008, 0.0026], motion_status: "scaled",
  endpoint_progress_status: "progressing", endpoint_progress_measurement_available: true,
  source_active: true, zero_input: false, stale_reason: null,
});
assert.deepEqual(complete.requested.desiredEndpointM, [0.3, 0.4, 0.5]);
assert.deepEqual(complete.resolved.worldEndpointVelocityMS, [-0.02, 0.01, 0.03]);
assert.deepEqual(complete.predicted.achievedDeltaM, [-0.0018, 0.0009, 0.0027]);
assert.deepEqual(complete.measured.actualTipDeltaM, [-0.0017, 0.0008, 0.0026]);
assert.deepEqual(complete.source, { active: true, zeroInput: false, staleReason: null });
assert.equal(complete.status.stale, false);

const malformed = buildEndpointPresentationState({
  desired_endpoint_m: [0, "bad", 0] as unknown as [number, number, number],
  endpoint_delta_achieved_m: [0, Number.NaN, 0], actual_tip_delta_m: null as unknown as [number, number, number],
});
assert.equal(malformed.requested.desiredEndpointM, null);
assert.equal(malformed.predicted.achievedDeltaM, null);
assert.equal(malformed.measured.actualTipDeltaM, null);
assert.match(formatEndpointPresentationText(malformed), /measured actual tip delta_m: unavailable/);

const unavailable = buildEndpointPresentationState({
  requested_control_frame: "tool", control_frame_resolution_status: "tool_orientation_unavailable",
  control_frame_resolution_reason: "tip_orientation_missing", motion_status: "held", target_rejected: true,
  stale_reason: "command_timeout", endpoint_progress_status: "measurement_unavailable",
  endpoint_progress_measurement_available: false,
});
assert.deepEqual(unavailable.status, {
  motion: "held", held: true, rejected: true, stale: true,
  resolutionUnavailable: true, measurementUnavailable: true,
});
assert.equal(unavailable.resolved.worldEndpointVelocityMS, null);

assert.equal(buildEndpointPresentationState({ runtime_input_safety_applied: false }).status.held, null);
assert.equal(buildEndpointPresentationState({
  motion_status: "accepted", runtime_input_safety_applied: true,
}).status.held, false);
assert.equal(buildEndpointPresentationState({
  motion_status: "held", runtime_input_safety_applied: false,
}).status.held, true);
assert.equal(buildEndpointPresentationState({
  motion_status: "invalid" as unknown as "held", runtime_input_safety_applied: true,
}).status.held, null);

assert.equal(buildEndpointPresentationState({ endpoint_progress_status: "not_requested" }).status.measurementUnavailable, null);
assert.equal(buildEndpointPresentationState({ endpoint_progress_status: "progressing" }).status.measurementUnavailable, false);
assert.equal(buildEndpointPresentationState({
  endpoint_progress_status: "progressing", endpoint_progress_measurement_available: false,
}).status.measurementUnavailable, true);

const inactive = buildEndpointPresentationState({ source_active: false, zero_input: true });
assert.deepEqual(inactive.source, { active: false, zeroInput: true, staleReason: null });
assert.equal(inactive.status.stale, false);
assert.equal(buildEndpointPresentationState({ stale_reason: null }).status.stale, false);
assert.equal(buildEndpointPresentationState({ stale_reason: "" }).status.stale, null);
assert.equal(buildEndpointPresentationState({ stale_reason: 17 as unknown as string }).status.stale, null);

const formatted = formatEndpointPresentationText(buildEndpointPresentationState({
  control_frame_resolution_reason: "tip_orientation_missing",
  source_active: false,
  zero_input: true,
  stale_reason: "command_timeout",
}));
assert.match(formatted, /resolution reason: tip_orientation_missing/);
assert.match(formatted, /source active: false/);
assert.match(formatted, /zero input: true/);
assert.match(formatted, /stale reason: command_timeout/);

const compatibility = buildEndpointPresentationState({ control_frame: "world", endpoint_delta_m: [0.1, 0, 0] });
assert.equal(compatibility.requested.controlFrame, "world");
assert.deepEqual(compatibility.predicted.requestedDeltaM, [0.1, 0, 0]);
const canonicalWins = buildEndpointPresentationState({
  requested_control_frame: "invalid" as unknown as "world", control_frame: "world",
  endpoint_delta_requested_m: [0, Number.NaN, 0], endpoint_delta_m: [0.1, 0, 0],
});
assert.equal(canonicalWins.requested.controlFrame, null);
assert.equal(canonicalWins.predicted.requestedDeltaM, null);

console.log("endpoint presentation tests passed");
