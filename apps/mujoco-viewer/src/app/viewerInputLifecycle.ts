import {
  createDefaultViewerInputProviderRegistry,
  type ViewerInputProvider,
  type ViewerInputProviderDocumentLike,
  type ViewerInputProviderId,
  type ViewerInputProviderOptions,
  type ViewerInputProviderRegistry,
  type ViewerInputProviderWindowLike,
} from "../input/viewerInputProvider.js";

export type ViewerKeyboardEventLike = import("../input/viewerInputProvider.js").ViewerKeyboardEventLike;
export type ViewerInputLifecycleWindowLike = ViewerInputProviderWindowLike;
export type ViewerInputLifecycleDocumentLike = ViewerInputProviderDocumentLike;

export interface ViewerInputLifecycleOptions extends ViewerInputProviderOptions {
  providerRegistry?: ViewerInputProviderRegistry;
  providerIds?: readonly ViewerInputProviderId[];
}

export interface ViewerInputLifecycle {
  setLiveInputEnabled(enabled: boolean): void;
  dispose(): void;
}

const DEFAULT_PROVIDER_IDS: readonly ViewerInputProviderId[] = ["gamepad/v1", "keyboard/v1"];

export function createViewerInputLifecycle(options: ViewerInputLifecycleOptions): ViewerInputLifecycle {
  const registry = options.providerRegistry ?? createDefaultViewerInputProviderRegistry();
  const providerIds = options.providerIds ?? DEFAULT_PROVIDER_IDS;
  const providers: ViewerInputProvider[] = [];
  let liveInputEnabled = false;
  let active = false;

  const disposeActiveInputs = (): void => {
    if (!active) return;
    active = false;
    for (const provider of [...providers].reverse()) provider.dispose();
    providers.length = 0;
  };

  const activateInputs = (): void => {
    if (active || !liveInputEnabled) return;
    if (new Set(providerIds).size !== providerIds.length) {
      throw new Error("duplicate viewer input provider selection");
    }

    const created: ViewerInputProvider[] = [];
    try {
      for (const id of providerIds) created.push(registry.create(id, options));
      for (const provider of created) provider.start();
    } catch (error) {
      for (const provider of [...created].reverse()) provider.dispose();
      throw error;
    }
    providers.push(...created);
    active = true;
  };

  return {
    setLiveInputEnabled(enabled): void {
      liveInputEnabled = enabled;
      if (enabled) activateInputs();
      else disposeActiveInputs();
    },
    dispose(): void {
      liveInputEnabled = false;
      disposeActiveInputs();
    },
  };
}
