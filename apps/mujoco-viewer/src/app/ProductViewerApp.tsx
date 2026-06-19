import { useEffect, useMemo, useRef, useState } from "react";
import { readViewerEndpointConfig } from "../config/websocketEndpoint.js";
import { formatQpos } from "../wasm-scene/mujocoQposSync.js";
import {
  createInitialProductViewerState,
  type ProductViewerState,
} from "../wasm-scene/productViewerState.js";
import { VISUAL_LEGEND_ITEMS } from "../wasm-scene/visualStyles.js";
import { createMujocoSceneRenderer } from "../wasm-scene/mujocoSceneRenderer.js";
import "./productViewer.css";

function formatNumber(value: number | null): string {
  if (value === null) {
    return "n/a";
  }

  return Number.isInteger(value) ? String(value) : value.toFixed(6);
}

function Legend() {
  const legendItems = useMemo(
    () => VISUAL_LEGEND_ITEMS,
    [],
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

export function ProductViewerApp() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [state, setState] = useState<ProductViewerState>(() => createInitialProductViewerState());
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

    const renderer = createMujocoSceneRenderer({
      canvas,
      modelPath: state.modelPath,
      fixturePath: state.fixturePath,
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
  }, [endpointConfig.websocketUrl, state.fixturePath, state.modelPath]);

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
              <dt>Debug fixture path</dt>
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
          <div className="viewer-subtle">qpos path is render-only</div>
        </div>
        <pre className="viewer-status">{state.statusText}</pre>
        {state.qposError === null ? null : <div className="viewer-error">{state.qposError}</div>}
      </section>

      <section className="viewer-panel viewer-panel--legend">
        <div className="viewer-status__header">
          <h2>Legend</h2>
          <div className="viewer-subtle">shared colors</div>
        </div>
        <Legend />
      </section>
    </main>
  );
}
