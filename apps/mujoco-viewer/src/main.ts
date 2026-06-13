import { payloadV0Fixture } from "./fixtures/payloadV0.js";
import { createViewerRuntime, type ViewerRuntime } from "./viewerRuntime.js";

function registerLifecycle(runtime: ViewerRuntime): void {
  if (typeof window === "undefined") {
    return;
  }

  const stop = () => runtime.stop();
  window.addEventListener("pagehide", stop, { once: true });
  window.addEventListener("beforeunload", stop, { once: true });
}

export function bootstrapViewerRuntime(): ViewerRuntime {
  const runtime = createViewerRuntime({ payload: payloadV0Fixture });
  runtime.start();
  registerLifecycle(runtime);
  return runtime;
}

export const viewerRuntime =
  typeof document === "undefined" ? null : bootstrapViewerRuntime();
