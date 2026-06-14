import type {
  PayloadArmSkeletonScene,
  PayloadArmSkeletonSegmentRenderSpec,
  TransportBodyPayload,
  TransportPayloadV0,
  TransportSitePayload,
} from "../types/transportPayload.js";

const CANONICAL_ARM_SKELETON_COLOR = "#22c55e";
const CANONICAL_ARM_SKELETON_BODY_NAME = "base_link";
const CANONICAL_ARM_SKELETON_SITE_NAME = "tip";

interface ArmSkeletonConnectionSpec {
  startBodyName: string;
  endSiteName: string;
  segmentName: string;
  label: string;
}

const ARM_SKELETON_CONNECTIONS: readonly ArmSkeletonConnectionSpec[] = [
  {
    startBodyName: CANONICAL_ARM_SKELETON_BODY_NAME,
    endSiteName: CANONICAL_ARM_SKELETON_SITE_NAME,
    segmentName: "base_link_to_tip",
    label: "base_link -> tip",
  },
];

function buildArmSkeletonSegment(
  connection: ArmSkeletonConnectionSpec,
  startBody: TransportBodyPayload,
  endSite: TransportSitePayload,
): PayloadArmSkeletonSegmentRenderSpec {
  return {
    kind: "arm_skeleton_segment",
    name: connection.segmentName,
    start_m: startBody.position_m,
    end_m: endSite.position_m,
    color: CANONICAL_ARM_SKELETON_COLOR,
    label: connection.label,
  };
}

function hasCanonicalArmSkeletonEndpoint(payload: TransportPayloadV0): boolean {
  return (
    payload.bodies.some((body) => body.name === CANONICAL_ARM_SKELETON_BODY_NAME) ||
    payload.sites.some((site) => site.name === CANONICAL_ARM_SKELETON_SITE_NAME)
  );
}

export function buildPayloadArmSkeletonScene(payload: TransportPayloadV0): PayloadArmSkeletonScene {
  const segments: PayloadArmSkeletonSegmentRenderSpec[] = [];

  for (const connection of ARM_SKELETON_CONNECTIONS) {
    const startBody = payload.bodies.find((body) => body.name === connection.startBodyName) ?? null;
    const endSite = payload.sites.find((site) => site.name === connection.endSiteName) ?? null;

    if (startBody === null || endSite === null) {
      continue;
    }

    segments.push(buildArmSkeletonSegment(connection, startBody, endSite));
  }

  const status =
    segments.length > 0
      ? "present"
      : hasCanonicalArmSkeletonEndpoint(payload)
        ? "partial"
        : "absent";

  return {
    status,
    segments,
  };
}

export function getCanonicalArmSkeletonConnectionNames(): readonly string[] {
  return ARM_SKELETON_CONNECTIONS.flatMap((connection) => [
    connection.startBodyName,
    connection.endSiteName,
  ]);
}
