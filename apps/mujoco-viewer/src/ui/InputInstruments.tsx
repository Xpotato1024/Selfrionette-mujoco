import type { ProductViewerState } from "../wasm-scene/productViewerState.js";
import { loadcellDisplayValues, signedBar } from "../app/instrumentPresentation.js";

function SignalBar({ value, scale, label, number }: { value: number; scale: number; label: string; number: number | null }) {
  const bar = signedBar(value, scale);
  return <div className="signal-row"><span>{label}</span><div className="signal-track" aria-hidden="true"><i className="signal-zero" />{bar !== null && <i className="signal-fill" style={{ left: `${bar.left}%`, width: `${bar.width}%` }} />}</div><output>{number === null ? "—" : number.toFixed(2)}</output></div>;
}

export function InputInstruments({ state, numbers }: { state: ProductViewerState; numbers: ProductViewerState }) {
  const input = state.inputOverlay;
  if (input === null) return <p className="instrument-empty">入力信号未取得</p>;
  const channels = input.sourceKind === "selfrionette" ? loadcellDisplayValues(input.rawSignal) : null;
  const labelChannels = loadcellDisplayValues(numbers.inputOverlay?.rawSignal ?? null);
  if (channels !== null) {
    const peak = Math.max(...channels.map(Math.abs));
    const scale = peak === 0 ? 1 : peak;
    return <div className="input-instruments" data-testid="loadcell-instruments" data-stale={input.staleReason !== null}>
      {channels.map((value, index) => <SignalBar key={index} label={`CH${index + 1}`} value={value} scale={scale} number={labelChannels?.[index] ?? null} />)}
      <p className="instrument-caption">生の7ch値 · 力単位/指対応は未校正<br />バーは同一sample内の相対比（±{scale.toPrecision(3)}）</p>
    </div>;
  }
  if (input.sourceKind.includes("gamepad")) {
    const axes = input.gamepadInstrumentAxes;
    const labeled = numbers.inputOverlay?.gamepadInstrumentAxes ?? [];
    const pressed = input.gamepadInstrumentPressedButtons;
    const hasXY = axes.length >= 2;
    return <div className="input-instruments" data-testid="gamepad-instruments" data-stale={input.staleReason !== null || input.gamepadStale === true}>
      <div className="gamepad-display"><svg viewBox="0 0 90 90" className="stick-indicator" role="img" aria-label={hasXY ? `axes 0/1: ${axes[0]}, ${axes[1]}` : "axes未取得"}>
        <rect x="9" y="9" width="72" height="72" rx="3" className="stick-bound" />
        <path d="M9 45H81M45 9V81" className="stick-cross" />
        {hasXY && <circle cx={45 + axes[0] * 36} cy={45 + axes[1] * 36} r="4" className="stick-point" />}
      </svg><div><strong>{input.gamepadConnected === null ? "接続情報なし" : input.gamepadConnected ? "接続" : "切断"}</strong><span>AXIS 0 / 1</span><span>wire normalized axes</span></div></div>
      {axes.length ? axes.map((value, index) => <SignalBar key={index} label={`A${index}`} value={value} scale={1} number={labeled[index] ?? null} />) : <p className="instrument-empty">axes未取得・不正</p>}
      <p className="instrument-caption">押下: {pressed === null ? "buttons情報不正" : pressed.length ? pressed.map((index) => `B${index}`).join(" / ") : "なし"}</p>
    </div>;
  }
  if (input.sourceKind.includes("keyboard")) {
    return <div className="keyboard-instruments" aria-label="backendが記録した押下キー">
      {([['KeyW', 'W'], ['KeyA', 'A'], ['KeyS', 'S'], ['KeyD', 'D'], ['Space', 'Space'], ['ShiftLeft', 'Shift']] as const).map(([code, label]) =>
        <kbd key={code} data-active={input.keyboardActiveKeyCodes.includes(code) || (code === 'ShiftLeft' && input.keyboardActiveKeyCodes.includes('ShiftRight'))}>{label}</kbd>)}
      <p className="instrument-caption">backend記録 · {input.keyboardFocusState ?? "focus未取得"}</p>
    </div>;
  }
  return <p className="instrument-empty">この入力の表示信号は未取得です</p>;
}
