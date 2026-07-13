import { FAST_ARM_VIEWER_PROFILE } from "./fastArm.js";
import type { ViewerRobotProfile } from "./types.js";

export class ViewerRobotProfileRegistry {
  readonly #profiles: ReadonlyMap<string, ViewerRobotProfile>;

  constructor(profiles: readonly ViewerRobotProfile[]) {
    const values = new Map<string, ViewerRobotProfile>();
    for (const profile of profiles) {
      if (values.has(profile.profileId)) {
        throw new Error(`duplicate viewer robot profile registration: ${profile.profileId}`);
      }
      values.set(profile.profileId, profile);
    }
    this.#profiles = values;
  }

  ids(): readonly string[] {
    return Object.freeze(Array.from(this.#profiles.keys()));
  }

  resolve(profileId: string): ViewerRobotProfile {
    const profile = this.#profiles.get(profileId);
    if (profile === undefined) {
      throw new Error(
        `unknown viewer robot profile ID ${JSON.stringify(profileId)}; available: ${this.ids().join(", ")}`,
      );
    }
    return profile;
  }
}

export const VIEWER_ROBOT_PROFILE_REGISTRY = new ViewerRobotProfileRegistry([
  FAST_ARM_VIEWER_PROFILE,
]);

export function resolveViewerRobotProfile(profileId: string): ViewerRobotProfile {
  return VIEWER_ROBOT_PROFILE_REGISTRY.resolve(profileId);
}
