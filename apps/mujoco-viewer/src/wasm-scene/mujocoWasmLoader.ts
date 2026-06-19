import loadMujoco from "@mujoco/mujoco";
import mujocoWasmUrl from "@mujoco/mujoco/mujoco.wasm?url";

export async function loadMujocoWasm(): Promise<any> {
  return loadMujoco({
    locateFile: (file: string) => (file === "mujoco.wasm" ? mujocoWasmUrl : file),
  });
}
