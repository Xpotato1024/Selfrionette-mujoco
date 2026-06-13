import { readViewerEndpointConfig } from "./config/websocketEndpoint.js";
import { payloadV0Fixture } from "./fixtures/payloadV0.js";
import { createViewerRuntime, type ViewerRuntime } from "./viewerRuntime.js";

function getViewerEndpointConfig() {
  if (typeof window === "undefined") {
    return {
      websocketUrl: null,
      source: "disabled" as const,
    };
  }

  return readViewerEndpointConfig(window.location);
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
  const endpointConfig = getViewerEndpointConfig();
  const runtime = createViewerRuntime({
    payload: payloadV0Fixture,
    websocketUrl: endpointConfig.websocketUrl,
  });
  runtime.start();
  registerLifecycle(runtime);
  return runtime;
}

export const viewerRuntime =
  typeof document === "undefined" ? null : bootstrapViewerRuntime();
