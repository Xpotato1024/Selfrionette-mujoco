import { loadFastArmViewerProfile } from "./fastArm.js";
import type { ViewerRobotProfile } from "./types.js";

/** profileId重複とunknown selectionを拒否するread-only viewer registry。 */
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

/** plugin-owned declarationを読み、失敗時に別Robot profileへfallbackしない。 */
export async function loadDefaultViewerRobotProfile(
  fetcher: typeof fetch = fetch,
): Promise<ViewerRobotProfile> {
  return loadFastArmViewerProfile(fetcher);
}
