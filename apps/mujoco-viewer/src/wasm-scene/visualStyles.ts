export const BODY_VISUAL_STYLES = {
  floor: { color: "#c7d2fe", label: "floor", detail: "ground plane" },
  origin: { color: "#f59e0b", label: "origin", detail: "reference marker" },
  base_link: { color: "#c2410c", label: "base_link", detail: "base housing" },
  sholder_link_1: { color: "#b91c1c", label: "sholder_link_1", detail: "first shoulder link" },
  sholder_link_2: { color: "#ea580c", label: "sholder_link_2", detail: "second shoulder link" },
  upper_arm_link: { color: "#15803d", label: "upper_arm_link", detail: "upper arm" },
  fore_arm_link: { color: "#0284c7", label: "fore_arm_link", detail: "forearm" },
} as const;

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
