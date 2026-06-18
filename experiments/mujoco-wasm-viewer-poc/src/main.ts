import { createMujocoFastArmViewer } from "./mujocoFastArmViewer.js";

const app = document.querySelector<HTMLDivElement>("#app");
if (app === null) {
  throw new Error("app root not found");
}

const viewer = createMujocoFastArmViewer({
  modelPath: "/assets/mujoco/fast_arm/scene.xml",
  mount: app,
});

void viewer.start();
