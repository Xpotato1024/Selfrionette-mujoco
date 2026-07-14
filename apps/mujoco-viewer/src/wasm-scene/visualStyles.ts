import type {
  ViewerBodyVisualStyle,
  ViewerRobotProfile,
} from "../robot-profiles/types.js";

export type BodyVisualStyle = ViewerBodyVisualStyle;

export function resolveBodyVisualStyle(
  profile: ViewerRobotProfile,
  bodyName: string,
  meshName: string,
  geomName: string,
): BodyVisualStyle | null {
  for (const candidate of [bodyName, meshName, geomName]) {
    const normalized = candidate.replace(/[^a-z0-9]/gi, "").toLowerCase();
    if (normalized === "") {
      continue;
    }
    const styleKey = profile.visualStyleSelection.get(normalized);
    if (styleKey !== undefined) {
      return profile.bodyVisualStyles[styleKey] ?? null;
    }
  }
  return null;
}

export function viewerVisualLegend(profile: ViewerRobotProfile): readonly ViewerBodyVisualStyle[] {
  return Object.freeze([
    ...Object.values(profile.bodyVisualStyles),
    ...profile.axisVisualStyles,
  ]);
}
