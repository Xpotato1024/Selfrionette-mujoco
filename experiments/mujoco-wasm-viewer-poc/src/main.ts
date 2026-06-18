import { createMujocoFastArmViewer } from "./mujocoFastArmViewer.js";

const app = document.querySelector<HTMLDivElement>("#app");
if (app === null) {
  throw new Error("app root not found");
}

const viewer = createMujocoFastArmViewer({
  modelPath: "/assets/mujoco/fast_arm/scene.xml",
  fixturePath: "/fixtures/fast_arm_sweep_x_qpos.json",
  mount: app,
});

void viewer.start();
