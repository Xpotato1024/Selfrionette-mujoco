import { loadViewerRobotDeclaration } from "./declaration.js";
import type { ViewerRobotProfile } from "./types.js";

/** Legacy static-viewer facade. The plugin-owned JSON remains the declaration SoT. */
export const FAST_ARM_VIEWER_DECLARATION_URL = "/assets/mujoco/fast_arm/viewer-profile.json";

export function loadFastArmViewerProfile(fetcher: typeof fetch = fetch): Promise<ViewerRobotProfile> {
  return loadViewerRobotDeclaration(FAST_ARM_VIEWER_DECLARATION_URL, fetcher);
}
