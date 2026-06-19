export interface BodyVisualStyle {
  color: string;
  label: string;
  detail: string;
  emissive?: string;
  emissiveIntensity?: number;
}

export const BODY_VISUAL_STYLES = {
  floor: { color: "#c7d2fe", label: "floor", detail: "ground plane" },
  origin: { color: "#f59e0b", label: "origin", detail: "reference marker" },
  base_link: { color: "#c2410c", label: "base_link", detail: "base housing" },
  sholder_link_1: { color: "#b91c1c", label: "sholder_link_1", detail: "first shoulder link" },
  sholder_link_2: { color: "#ea580c", label: "sholder_link_2", detail: "second shoulder link" },
  upper_arm_link: {
    color: "#22c55e",
    label: "upper_arm_link",
    detail: "upper arm",
    emissive: "#22c55e",
    emissiveIntensity: 0.16,
  },
  fore_arm_link: {
    color: "#06b6d4",
    label: "fore_arm_link",
    detail: "forearm",
    emissive: "#06b6d4",
    emissiveIntensity: 0.16,
  },
} as const satisfies Record<string, BodyVisualStyle>;

export const AXIS_VISUAL_STYLES = [
  { label: "axes X", color: "#ef4444", detail: "positive X" },
  { label: "axes Y", color: "#22c55e", detail: "positive Y" },
  { label: "axes Z", color: "#3b82f6", detail: "positive Z" },
] as const;

export const VISUAL_LEGEND_ITEMS = [
  BODY_VISUAL_STYLES.floor,
  BODY_VISUAL_STYLES.origin,
  BODY_VISUAL_STYLES.base_link,
  BODY_VISUAL_STYLES.sholder_link_1,
  BODY_VISUAL_STYLES.sholder_link_2,
  BODY_VISUAL_STYLES.upper_arm_link,
  BODY_VISUAL_STYLES.fore_arm_link,
  ...AXIS_VISUAL_STYLES,
] as const;

const VISUAL_STYLE_KEY_BY_NAME = new Map<string, keyof typeof BODY_VISUAL_STYLES>([
  ["world", "floor"],
  ["floor", "floor"],
  ["origin", "origin"],
  ["base", "base_link"],
  ["base_link", "base_link"],
  ["baselink", "base_link"],
  ["sholder_link_1", "sholder_link_1"],
  ["sholderlink1", "sholder_link_1"],
  ["sholder_link_2", "sholder_link_2"],
  ["sholderlink2", "sholder_link_2"],
  ["upper_arm_link", "upper_arm_link"],
  ["upperarmlink", "upper_arm_link"],
  ["fore_arm_link", "fore_arm_link"],
  ["forearmlink", "fore_arm_link"],
]);

export function resolveBodyVisualStyleKey(bodyName: string, meshName: string, geomName: string): keyof typeof BODY_VISUAL_STYLES | null {
  const candidates = [bodyName, meshName, geomName];
  for (const candidate of candidates) {
    const normalized = candidate.replace(/[^a-z0-9]/gi, "").toLowerCase();
    if (normalized === "") {
      continue;
    }

    const styleKey = VISUAL_STYLE_KEY_BY_NAME.get(normalized);
    if (styleKey !== undefined) {
      return styleKey;
    }
  }

  return null;
}
