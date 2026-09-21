/** React表示だけをcoalesceする。renderer、input取得、安全判定、実験記録へ戻さない。 */
import type { ProductViewerState } from "../wasm-scene/productViewerState.js";

export function presentationCriticalKey(state: ProductViewerState): string {
  const input = state.inputOverlay;
  const contact = state.contactTaskPresentation;
  const ingress = state.viewerTiming?.latestIngressStatus;
  return JSON.stringify([
    state.robotProfileId, state.connectionStatus, state.status, state.qposStatus, state.qposError,
    state.currentQpos === null, Boolean(state.jointLayout),
    input?.sourceKind, input?.sourceActive, input?.staleReason, input?.targetRejected,
    input?.motionStatus, input?.motionRejectionReason, input?.gamepadConnected, input?.gamepadStale,
    input?.keyboardActiveKeyCodes, input?.keyboardFocusState, input?.gamepadInstrumentPressedButtons,
    input?.rawSignal?.source, input?.rawSignal?.sampleSchema, input?.gamepadInstrumentAxes.length,
    input?.targetStatus, input?.targetRejectionReason, input?.runtimeInputSafetyApplied,
    input?.endpointEvaluationState, input?.endpointPresentation.status,
    ingress === "parse_error" || ingress === "compatibility_invalid",
    contact.status, contact.reason, contact.taskState?.phase, contact.taskState?.classification,
  ]);
}

export function createPresentationCadence<T>(options: {
  intervalMs: number;
  criticalKey: (value: T) => string;
  deliver: (value: T) => void;
  now?: () => number;
  schedule?: (callback: () => void, delay: number) => ReturnType<typeof setTimeout>;
  cancel?: (handle: ReturnType<typeof setTimeout>) => void;
}): { push(value: T): void; discardPending(): void; dispose(): void } {
  if (!Number.isFinite(options.intervalMs) || options.intervalMs <= 0) throw new Error("invalid presentation interval");
  const now = options.now ?? (() => performance.now());
  const schedule = options.schedule ?? setTimeout;
  const cancel = options.cancel ?? clearTimeout;
  let disposed = false;
  let lastKey: string | null = null;
  let lastDelivered = -Infinity;
  let pending: T | null = null;
  let handle: ReturnType<typeof setTimeout> | null = null;
  const clearPending = (): void => {
    if (handle !== null) cancel(handle);
    handle = null;
    pending = null;
  };
  const emit = (value: T): void => {
    lastDelivered = now();
    lastKey = options.criticalKey(value);
    options.deliver(value);
  };
  return {
    push(value): void {
      if (disposed) return;
      if (lastKey !== options.criticalKey(value) || now() - lastDelivered >= options.intervalMs) {
        clearPending();
        emit(value);
        return;
      }
      pending = value;
      if (handle === null) handle = schedule(() => {
        handle = null;
        const value = pending;
        pending = null;
        if (!disposed && value !== null) emit(value);
      }, Math.max(0, options.intervalMs - (now() - lastDelivered)));
    },
    discardPending: clearPending,
    dispose(): void {
      disposed = true;
      clearPending();
    },
  };
}
