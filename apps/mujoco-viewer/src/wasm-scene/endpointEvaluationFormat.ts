import type { TransportEndpointEvaluationPayload } from "../types/transportPayload.js";

function formatNumber(value: number, maximumFractionDigits = 4): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(maximumFractionDigits);
}

function formatNumberList(values: readonly number[], maximumFractionDigits = 4): string {
  return `[${values.map((value) => formatNumber(value, maximumFractionDigits)).join(", ")}]`;
}

export function formatEndpointEvaluationVector(values: readonly number[] | null): string {
  return values === null ? "n/a" : formatNumberList(values, 4);
}

export function formatEndpointEvaluationAngles(values: readonly number[] | null): string {
  return values === null ? "n/a" : formatNumberList(values, 4);
}

export function formatEndpointEvaluationScalar(value: number | null): string {
  return value === null ? "n/a" : formatNumber(value, 4);
}

export function formatEndpointEvaluationSummary(
  endpointEvaluation: TransportEndpointEvaluationPayload | null,
): string {
  if (endpointEvaluation === null) {
    return "Endpoint evaluation: unavailable";
  }

  return [
    "Endpoint evaluation",
    `- desired: ${formatEndpointEvaluationVector(endpointEvaluation.desired_endpoint_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`,
    `- qpos-like joint angles: ${formatEndpointEvaluationAngles(endpointEvaluation.qpos_like_joint_angles_rad ?? null)} rad`,
    `- FK: ${formatEndpointEvaluationVector(endpointEvaluation.fk_endpoint_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`,
    `- site: ${formatEndpointEvaluationVector(endpointEvaluation.site_endpoint_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`,
    `- desired -> FK error: ${formatEndpointEvaluationVector(endpointEvaluation.desired_to_fk_error_vector_m ?? null)} |norm| ${formatEndpointEvaluationScalar(endpointEvaluation.desired_to_fk_error_norm_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`,
    `- desired -> site error: ${formatEndpointEvaluationVector(endpointEvaluation.desired_to_site_error_vector_m ?? null)} |norm| ${formatEndpointEvaluationScalar(endpointEvaluation.desired_to_site_error_norm_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`,
    `- FK -> site error: ${formatEndpointEvaluationVector(endpointEvaluation.fk_to_site_error_vector_m ?? null)} |norm| ${formatEndpointEvaluationScalar(endpointEvaluation.fk_to_site_error_norm_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`,
    "- frames:",
    `  desired: ${endpointEvaluation.desired_endpoint_coordinate_frame ?? "n/a"}`,
    `  FK: ${endpointEvaluation.fk_endpoint_coordinate_frame ?? "n/a"}`,
    `  site: ${endpointEvaluation.site_endpoint_coordinate_frame ?? "n/a"}`,
    `- note: ${endpointEvaluation.frame_mismatch_note ?? "n/a"}`,
  ].join("\n");
}
