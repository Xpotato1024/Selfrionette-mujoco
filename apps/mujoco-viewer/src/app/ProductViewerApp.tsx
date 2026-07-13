import { useEffect, useMemo, useRef, useState } from "react";
import { readViewerEndpointConfig } from "../config/websocketEndpoint.js";
import {
  createViewerKeyboardCapture,
  createViewerKeyboardControlSender,
  DEFAULT_VIEWER_KEYBOARD_BINDINGS,
} from "../input/keyboardInput.js";
import {
  createViewerGamepadControlSender,
  type ViewerGamepadLike,
} from "../input/gamepadInput.js";
import { createViewerGamepadLifecycle } from "./gamepadLifecycle.js";
import { formatQpos } from "../wasm-scene/mujocoQposSync.js";
import {
  formatEndpointEvaluationAngles,
  formatEndpointEvaluationScalar,
  formatEndpointEvaluationVector,
} from "../wasm-scene/endpointEvaluationFormat.js";
import {
  createInitialProductViewerState,
  formatInputOverlayText,
  type ProductViewerState,
} from "../wasm-scene/productViewerState.js";
import { createMujocoSceneRenderer } from "../wasm-scene/mujocoSceneRenderer.js";
import { resolveViewerRobotProfile } from "../robot-profiles/registry.js";
import type { ViewerRobotProfile } from "../robot-profiles/types.js";
import { viewerVisualLegend } from "../wasm-scene/visualStyles.js";
import "./productViewer.css";

function formatNumber(value: number | null): string {
  if (value === null) {
    return "n/a";
  }

  return Number.isInteger(value) ? String(value) : value.toFixed(6);
}

function Legend({ profile }: { profile: ViewerRobotProfile | null }) {
  const legendItems = useMemo(
    () => (profile === null ? [] : viewerVisualLegend(profile)),
    [profile],
  );

  return (
    <div className="viewer-legend">
      {legendItems.map((item) => (
        <div className="viewer-legend__item" key={item.label}>
          <span className="viewer-legend__swatch" style={{ background: item.color }} />
          <div className="viewer-legend__text">
            <strong>{item.label}</strong>
            <span>{item.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function EndpointEvaluationPanel({ state }: { state: ProductViewerState }) {
  const endpointEvaluation = state.endpointEvaluation;
  if (endpointEvaluation === null) {
    return <div className="viewer-endpoint-evaluation__empty">Endpoint evaluation: unavailable</div>;
  }

  return (
    <dl className="viewer-endpoint-evaluation__kv">
      <div>
        <dt>Desired</dt>
        <dd>{`${formatEndpointEvaluationVector(endpointEvaluation.desired_endpoint_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`}</dd>
      </div>
      <div>
        <dt>qpos-like joint angles</dt>
        <dd>{`${formatEndpointEvaluationAngles(endpointEvaluation.qpos_like_joint_angles_rad ?? null)} rad`}</dd>
      </div>
      <div>
        <dt>FK</dt>
        <dd>{`${formatEndpointEvaluationVector(endpointEvaluation.fk_endpoint_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`}</dd>
      </div>
      <div>
        <dt>Site</dt>
        <dd>{`${formatEndpointEvaluationVector(endpointEvaluation.site_endpoint_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`}</dd>
      </div>
      <div>
        <dt>Desired -&gt; FK error</dt>
        <dd>
          {`${formatEndpointEvaluationVector(endpointEvaluation.desired_to_fk_error_vector_m ?? null)} |norm| ${formatEndpointEvaluationScalar(endpointEvaluation.desired_to_fk_error_norm_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`}
        </dd>
      </div>
      <div>
        <dt>Desired -&gt; site error</dt>
        <dd>
          {`${formatEndpointEvaluationVector(endpointEvaluation.desired_to_site_error_vector_m ?? null)} |norm| ${formatEndpointEvaluationScalar(endpointEvaluation.desired_to_site_error_norm_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`}
        </dd>
      </div>
      <div>
        <dt>FK -&gt; site error</dt>
        <dd>
          {`${formatEndpointEvaluationVector(endpointEvaluation.fk_to_site_error_vector_m ?? null)} |norm| ${formatEndpointEvaluationScalar(endpointEvaluation.fk_to_site_error_norm_m ?? null)} ${endpointEvaluation.unit ?? "n/a"}`}
        </dd>
      </div>
      <div>
        <dt>Frames</dt>
        <dd>
          <div>desired: {endpointEvaluation.desired_endpoint_coordinate_frame ?? "n/a"}</div>
          <div>FK: {endpointEvaluation.fk_endpoint_coordinate_frame ?? "n/a"}</div>
          <div>site: {endpointEvaluation.site_endpoint_coordinate_frame ?? "n/a"}</div>
        </dd>
      </div>
      <div>
        <dt>Note</dt>
        <dd>{endpointEvaluation.frame_mismatch_note ?? "n/a"}</dd>
      </div>
    </dl>
  );
}

function InputOverlayPanel({ state }: { state: ProductViewerState }) {
  return <pre className="viewer-input-overlay__text">{formatInputOverlayText(state.inputOverlay)}</pre>;
}

export function ProductViewerApp() {
  const profileResolution = useMemo(() => {
    const requestedProfileId =
      typeof window === "undefined"
        ? "fast_arm"
        : new URLSearchParams(window.location.search).get("robotProfileId") ?? "fast_arm";
    try {
      return { profile: resolveViewerRobotProfile(requestedProfileId), error: null as string | null };
    } catch (error) {
      return {
        profile: null,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }, []);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const keyboardCaptureRef = useRef(
    createViewerKeyboardCapture(
      DEFAULT_VIEWER_KEYBOARD_BINDINGS,
      typeof document !== "undefined" && document.hasFocus() ? "focused" : "blurred",
    ),
  );
  const [state, setState] = useState<ProductViewerState>(() =>
    createInitialProductViewerState(profileResolution.profile ?? undefined),
  );
  const endpointConfig = useMemo(() => {
    if (typeof window === "undefined") {
      return { websocketUrl: null as string | null };
    }

    return readViewerEndpointConfig(window.location);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) {
      return;
    }
    if (profileResolution.profile === null) {
      setState((current) => ({
        ...current,
        status: "error",
        qposStatus: "unavailable",
        qposError: profileResolution.error,
        statusText: profileResolution.error ?? "viewer robot profile unavailable",
      }));
      return;
    }

    const renderer = createMujocoSceneRenderer({
      canvas,
      profile: profileResolution.profile,
      websocketUrl: endpointConfig.websocketUrl,
      onStateChange: setState,
      onError(error) {
        setState((current) => ({
          ...current,
          status: "error",
          qposStatus: "unavailable",
          qposError: error.message,
          statusText: error.message,
        }));
      },
    });

    void renderer.start();
    return () => {
      renderer.dispose();
    };
  }, [endpointConfig.websocketUrl, profileResolution.error, profileResolution.profile]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof document === "undefined" || state.connectionStatus !== "open") {
      return;
    }

    const keyboardCapture = keyboardCaptureRef.current;
    const keyboardSender = createViewerKeyboardControlSender({
      url: endpointConfig.websocketUrl,
    });
    let disposed = false;
    let animationFrameId = 0;

    const publishKeyboardState = (): void => {
      keyboardSender.publish(keyboardCapture.snapshot(), undefined, {
        metadata: {
          intent_kind: "local_endpoint_velocity",
          input_continuity: "continuous",
          source_kind: "viewer_keyboard",
          control_frame: "world",
          local_endpoint_speed_m_s: 0.1,
          local_endpoint_max_delta_m: 0.03,
        },
      });
    };

    const scheduleKeyboardPublish = (): void => {
      if (disposed) {
        return;
      }

      publishKeyboardState();
      animationFrameId = window.requestAnimationFrame(scheduleKeyboardPublish);
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      if (!keyboardCapture.isBoundKey(event.code)) {
        return;
      }
      event.preventDefault();
      if (!keyboardCapture.handleKeyDown(event.code, event.repeat)) {
        return;
      }

      publishKeyboardState();
    };

    const onKeyUp = (event: KeyboardEvent): void => {
      if (!keyboardCapture.isBoundKey(event.code)) {
        return;
      }
      if (!keyboardCapture.handleKeyUp(event.code)) {
        return;
      }

      event.preventDefault();
      publishKeyboardState();
    };

    const onWindowBlur = (): void => {
      if (!keyboardCapture.handleBlur()) {
        return;
      }

      publishKeyboardState();
    };

    const onWindowFocus = (): void => {
      if (!keyboardCapture.handleFocus()) {
        return;
      }

      publishKeyboardState();
    };

    const onVisibilityChange = (): void => {
      if (!keyboardCapture.handleVisibilityChange(document.visibilityState === "visible")) {
        return;
      }

      publishKeyboardState();
    };

    publishKeyboardState();
    animationFrameId = window.requestAnimationFrame(scheduleKeyboardPublish);
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onWindowBlur);
    window.addEventListener("focus", onWindowFocus);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(animationFrameId);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onWindowBlur);
      window.removeEventListener("focus", onWindowFocus);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      keyboardSender.dispose();
    };
  }, [endpointConfig.websocketUrl, state.connectionStatus]);

  useEffect(() => {
    if (typeof window === "undefined" || typeof document === "undefined" || state.connectionStatus !== "open") {
      return;
    }

    const gamepadSender = createViewerGamepadControlSender({
      url: endpointConfig.websocketUrl,
    });
    const gamepadLifecycle = createViewerGamepadLifecycle({
      window,
      document,
      getGamepads: () => {
        if (typeof navigator === "undefined" || typeof navigator.getGamepads !== "function") {
          return null;
        }

        return navigator.getGamepads() as unknown as ArrayLike<ViewerGamepadLike | null | undefined>;
      },
      publish(snapshot) {
        gamepadSender.publish(snapshot);
      },
    });
    gamepadLifecycle.start();

    return () => {
      gamepadLifecycle.dispose();
      gamepadSender.dispose();
    };
  }, [endpointConfig.websocketUrl, state.connectionStatus]);

  const currentQposText = state.currentQpos === null ? "qpos unavailable" : formatQpos(state.currentQpos);

  return (
    <main className="viewer-shell">
      <header className="viewer-header">
        <div>
          <div className="viewer-eyebrow">product viewer</div>
          <h1>MuJoCo WASM scene renderer</h1>
          <p>Python native MuJoCo remains the source of truth. Browser WASM only renders the supplied qpos.</p>
        </div>
        <div className={`viewer-badge viewer-badge--${state.status}`}>{state.status}</div>
      </header>

      <div className="viewer-grid">
        <section className="viewer-panel viewer-panel--info">
          <h2>Runtime</h2>
          <dl className="viewer-kv">
            <div>
              <dt>Renderer mode</dt>
              <dd>{state.rendererMode}</dd>
            </div>
            <div>
              <dt>Connection</dt>
              <dd>{state.connectionStatus}</dd>
            </div>
            <div>
              <dt>Model path</dt>
              <dd>{state.modelPath}</dd>
            </div>
            <div>
              <dt>Debug fixture path (reference only)</dt>
              <dd>{state.fixturePath}</dd>
            </div>
            <div>
              <dt>Pose source</dt>
              <dd>{state.sourceLabel}</dd>
            </div>
            <div>
              <dt>Qpos status</dt>
              <dd>{state.qposStatus}</dd>
            </div>
          </dl>

          <h2>Model</h2>
          <dl className="viewer-kv">
            <div>
              <dt>nq</dt>
              <dd>{formatNumber(state.modelNq)}</dd>
            </div>
            <div>
              <dt>nv</dt>
              <dd>{formatNumber(state.modelNv)}</dd>
            </div>
            <div>
              <dt>ngeom</dt>
              <dd>{formatNumber(state.modelNgeom)}</dd>
            </div>
            <div>
              <dt>nmesh</dt>
              <dd>{formatNumber(state.modelNmesh)}</dd>
            </div>
            <div>
              <dt>Current frame</dt>
              <dd>{formatNumber(state.currentFrameIndex)}</dd>
            </div>
            <div>
              <dt>Timestamp_s</dt>
              <dd>{formatNumber(state.currentTimestampS)}</dd>
            </div>
          </dl>
        </section>

        <section className="viewer-panel viewer-panel--canvas">
          <div className="viewer-canvas__header">
            <div>
              <h2>Canvas</h2>
              <p>Floor, axes, and color legend are aligned to the compiled MuJoCo scene.</p>
            </div>
            <div className="viewer-subtle">mode: {state.rendererMode}</div>
          </div>
          <canvas ref={canvasRef} className="viewer-canvas" />
          <div className="viewer-canvas__footer">
            <div className="viewer-note">Current qpos</div>
            <code>{currentQposText}</code>
          </div>
        </section>
      </div>

        <section className="viewer-panel viewer-panel--status">
          <div className="viewer-status__header">
            <h2>Status</h2>
            <div className="viewer-subtle">qpos path is render-only; diagnostics are read-only</div>
          </div>
        <pre className="viewer-status">{state.statusText}</pre>
        {state.qposError === null ? null : <div className="viewer-error">{state.qposError}</div>}
        <div className="viewer-endpoint-evaluation">
          <div className="viewer-endpoint-evaluation__header">
            <h3>Endpoint evaluation</h3>
            <div className="viewer-subtle">read-only diagnostic overlay</div>
          </div>
          <EndpointEvaluationPanel state={state} />
        </div>
        <div className="viewer-input-overlay">
          <div className="viewer-input-overlay__header">
            <h3>Input overlay</h3>
            <div className="viewer-subtle">source, keys, axes, buttons, age, stale state</div>
          </div>
          <InputOverlayPanel state={state} />
        </div>
      </section>

      <section className="viewer-panel viewer-panel--legend">
        <div className="viewer-status__header">
          <h2>Legend</h2>
          <div className="viewer-subtle">shared colors</div>
        </div>
        <Legend profile={profileResolution.profile} />
      </section>
    </main>
  );
}
