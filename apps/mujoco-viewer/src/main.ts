import { payloadV0Fixture } from "./fixtures/payloadV0.js";
import { createViewerRuntime, type ViewerRuntime } from "./viewerRuntime.js";

function getWebSocketUrl(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  return new URL(window.location.href).searchParams.get("websocketUrl") ?? undefined;
}

function registerLifecycle(runtime: ViewerRuntime): void {
  if (typeof window === "undefined") {
    return;
  }

  const stop = () => runtime.stop();
  window.addEventListener("pagehide", stop, { once: true });
  window.addEventListener("beforeunload", stop, { once: true });
}

export function bootstrapViewerRuntime(): ViewerRuntime {
  const runtime = createViewerRuntime({
    payload: payloadV0Fixture,
    websocketUrl: getWebSocketUrl(),
  });
  runtime.start();
  registerLifecycle(runtime);
  return runtime;
}

export const viewerRuntime =
  typeof document === "undefined" ? null : bootstrapViewerRuntime();
