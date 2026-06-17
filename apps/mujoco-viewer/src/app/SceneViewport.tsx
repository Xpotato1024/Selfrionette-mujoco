import { useEffect, useRef } from "react";

interface SceneViewportProps {
  onCanvasReady?: (canvas: HTMLCanvasElement | null) => void;
  sceneText: string;
}

export function SceneViewport({ onCanvasReady, sceneText }: SceneViewportProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    onCanvasReady?.(canvas);

    return () => {
      onCanvasReady?.(null);
    };
  }, [onCanvasReady]);

  return (
    <section className="viewer-scene-panel" data-component="scene-viewport" data-role="viewer-scene">
      <header className="viewer-scene-panel__header">
        <h2 className="viewer-scene-panel__title">Scene</h2>
        <p className="viewer-scene-panel__subtitle">Three.js stays imperative inside the canvas island.</p>
      </header>
      <div className="viewer-scene-panel__canvas-shell">
        <canvas
          ref={canvasRef}
          className="viewer-scene-panel__canvas"
          data-role="viewer-scene-canvas"
          width={960}
          height={540}
        />
      </div>
      <p className="viewer-scene-panel__summary" data-role="viewer-scene-text">
        {sceneText}
      </p>
    </section>
  );
}
