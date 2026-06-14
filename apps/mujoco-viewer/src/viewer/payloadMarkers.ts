import type {
  CanonicalPayloadMarkers,
  PayloadErrorVectorRenderSpec,
  PayloadMarkerRenderSpec,
  PayloadMarkerScene,
  TransportBodyPayload,
  TransportPayloadV0,
  TransportSitePayload,
  Vector3,
} from "../types/transportPayload.js";

const BASE_LINK_NAME = "base_link";
const TIP_SITE_NAME = "tip";

function buildBodyMarker(body: TransportBodyPayload): PayloadMarkerRenderSpec {
  return {
    kind: "body",
    name: body.name,
    shape: body.name === BASE_LINK_NAME ? "cube" : "axes",
    position_m: body.position_m,
    quaternion_wxyz: body.quaternion_wxyz,
    color: body.name === BASE_LINK_NAME ? "#4f46e5" : "#64748b",
    label: body.name,
  };
}

function buildSiteMarker(site: TransportSitePayload): PayloadMarkerRenderSpec {
  return {
    kind: "site",
    name: site.name,
    shape: site.name === TIP_SITE_NAME ? "sphere" : "axes",
    position_m: site.position_m,
    quaternion_wxyz: site.quaternion_wxyz,
    color: site.name === TIP_SITE_NAME ? "#f97316" : "#0f766e",
    label: site.name,
  };
}

function buildTargetMarker(position_m: Vector3): PayloadMarkerRenderSpec {
  return {
    kind: "target",
    name: "target",
    shape: "sphere",
    position_m,
    color: "#ef4444",
    label: "target",
  };
}

function buildErrorVectorMarker(
  tipPosition_m: Vector3,
  targetPosition_m: Vector3,
): PayloadErrorVectorRenderSpec {
  return {
    kind: "error_vector",
    name: "tip_to_target",
    start_m: tipPosition_m,
    end_m: targetPosition_m,
    color: "#dc2626",
    label: "tip -> target",
  };
}

export function buildPayloadMarkerScene(payload: TransportPayloadV0): PayloadMarkerScene {
  const bodies = payload.bodies.map(buildBodyMarker);
  const sites = payload.sites.map(buildSiteMarker);
  const tipSite = payload.sites.find((site) => site.name === TIP_SITE_NAME) ?? null;
  const target = payload.target_position_m === null ? null : buildTargetMarker(payload.target_position_m);
  const errorVector =
    tipSite === null || payload.target_position_m === null
      ? null
      : buildErrorVectorMarker(tipSite.position_m, payload.target_position_m);

  return {
    bodies,
    sites,
    target,
    errorVector,
  };
}

export function getCanonicalPayloadMarkers(payload: TransportPayloadV0): CanonicalPayloadMarkers {
  return {
    baseLinkBody: payload.bodies.find((body) => body.name === BASE_LINK_NAME) ?? null,
    tipSite: payload.sites.find((site) => site.name === TIP_SITE_NAME) ?? null,
    targetPosition_m: payload.target_position_m,
  };
}
