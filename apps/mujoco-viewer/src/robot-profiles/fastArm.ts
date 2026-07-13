import type { ViewerRobotProfile } from "./types.js";

const bodyVisualStyles = Object.freeze({
  floor: { color: "#c7d2fe", label: "floor", detail: "ground plane" },
  origin: { color: "#f59e0b", label: "origin", detail: "reference marker" },
  base_link: { color: "#c2410c", label: "base_link", detail: "base housing" },
  sholder_link_1: { color: "#b91c1c", label: "sholder_link_1", detail: "first shoulder link" },
  sholder_link_2: { color: "#ea580c", label: "sholder_link_2", detail: "second shoulder link" },
  upper_arm_link: { color: "#15803d", label: "upper_arm_link", detail: "upper arm" },
  fore_arm_link: { color: "#0284c7", label: "fore_arm_link", detail: "forearm" },
});

const visualStyleSelection = new Map<string, string>([
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

export const FAST_ARM_VIEWER_PROFILE: ViewerRobotProfile = Object.freeze({
  profileId: "fast_arm",
  profileContractVersion: 1,
  modelContractVersion: "fast_arm-mujoco-model/v1",
  modelUrl: "/assets/mujoco/fast_arm/scene.xml",
  initialKeyframeName: "home",
  initialPoseSourceLabel: "MuJoCo home keyframe",
  fixtureUrl: "/fixtures/fast_arm_sweep_x_qpos.json",
  vfsAssets: new Map<string, string>([
    ["arm.xml", "/assets/mujoco/fast_arm/arm.xml"],
    ["meshes/BaseLink.stl", "/assets/mujoco/fast_arm/meshes/BaseLink.stl"],
    ["meshes/SholderLink1.stl", "/assets/mujoco/fast_arm/meshes/SholderLink1.stl"],
    ["meshes/SholderLink2.stl", "/assets/mujoco/fast_arm/meshes/SholderLink2.stl"],
    ["meshes/UpperArmLink.stl", "/assets/mujoco/fast_arm/meshes/UpperArmLink.stl"],
    ["meshes/ForeArmLink.stl", "/assets/mujoco/fast_arm/meshes/ForeArmLink.stl"],
  ]),
  meshFallbackUrls: new Map<string, string>([
    ["BaseLink", "/assets/mujoco/fast_arm/meshes/BaseLink.stl"],
    ["SholderLink1", "/assets/mujoco/fast_arm/meshes/SholderLink1.stl"],
    ["SholderLink2", "/assets/mujoco/fast_arm/meshes/SholderLink2.stl"],
    ["UpperArmLink", "/assets/mujoco/fast_arm/meshes/UpperArmLink.stl"],
    ["ForeArmLink", "/assets/mujoco/fast_arm/meshes/ForeArmLink.stl"],
  ]),
  visualStyleSelection,
  bodyVisualStyles,
  axisVisualStyles: Object.freeze([
    { label: "axes X", color: "#ef4444", detail: "positive X" },
    { label: "axes Y", color: "#22c55e", detail: "positive Y" },
    { label: "axes Z", color: "#3b82f6", detail: "positive Z" },
  ]),
  jointNames: Object.freeze([
    "sholder_joint_1",
    "sholder_joint_2",
    "sholder_joint_3",
    "elbow_joint",
  ]),
  qposDimension: 4,
});
