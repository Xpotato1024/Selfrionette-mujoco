import type { TransportPayloadV0 } from "../types/transportPayload";

export const payloadV0Fixture: TransportPayloadV0 = {
  version: 0,
  frame_index: 1,
  time_s: 0.0,
  qpos: [],
  qvel: [],
  bodies: [
    {
      name: "base_link",
      position_m: [0.0, 0.0, 0.0],
      quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
    },
  ],
  sites: [
    {
      name: "tip",
      position_m: [0.1, 0.2, 0.3],
      quaternion_wxyz: [1.0, 0.0, 0.0, 0.0],
    },
  ],
  target_position_m: null,
  metadata: {},
};
