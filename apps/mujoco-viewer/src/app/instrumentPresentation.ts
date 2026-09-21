/** 生信号の表示projectionを照合する。欠測、identity、unitを補完しない。 */
export interface RawInputSignal {
  readonly source: string;
  readonly sampleSchema: string;
  readonly sourceTimestampS: number;
  readonly values: readonly number[];
}

export function parseRawInputSignal(value: unknown, frameIndex: unknown, timestampS: unknown): RawInputSignal | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const keys = ["schema_version", "source", "sample_schema", "source_timestamp_s", "frame_index", "simulation_time_s", "values"];
  if (Object.keys(raw).length !== keys.length || keys.some((key) => !(key in raw)) ||
      raw.schema_version !== "input-signal-display/v1" ||
      typeof raw.source !== "string" || !raw.source || raw.source !== raw.source.trim() || raw.source.includes("\0") ||
      typeof raw.sample_schema !== "string" || !raw.sample_schema || raw.sample_schema !== raw.sample_schema.trim() || raw.sample_schema.includes("\0") ||
      typeof raw.source_timestamp_s !== "number" || !Number.isFinite(raw.source_timestamp_s) ||
      !Number.isSafeInteger(raw.frame_index) || (raw.frame_index as number) < 0 || raw.frame_index !== frameIndex ||
      typeof raw.simulation_time_s !== "number" || !Number.isFinite(raw.simulation_time_s) || raw.simulation_time_s !== timestampS ||
      !Array.isArray(raw.values) || !raw.values.every((item) => typeof item === "number" && Number.isFinite(item))) return null;
  return { source: raw.source, sampleSchema: raw.sample_schema, sourceTimestampS: raw.source_timestamp_s, values: [...raw.values] };
}

export function loadcellDisplayValues(signal: RawInputSignal | null): readonly number[] | null {
  return signal?.source === "selfrionette" && signal.sampleSchema === "loadcell_vector_sample/v1" && signal.values.length === 7
    ? signal.values : null;
}

/** 取得値の順序を維持する。不正要素だけ除去して軸番号をずらさない。 */
export function normalizedAxes(value: unknown): number[] {
  return Array.isArray(value) && value.every((item) => typeof item === "number" && Number.isFinite(item) && Math.abs(item) <= 1)
    ? [...value] : [];
}

export function signedBar(value: number, scale: number): { left: number; width: number } | null {
  if (!Number.isFinite(value) || !Number.isFinite(scale) || scale <= 0 || Math.abs(value) > scale) return null;
  const fraction = value / scale;
  return { left: 50 + Math.min(0, fraction * 50), width: Math.abs(fraction) * 50 };
}


export function pressedGamepadButtons(buttons: unknown): number[] | null {
  if (!Array.isArray(buttons)) return null;
  const pressed: number[] = [];
  for (let index = 0; index < buttons.length; index++) {
    const button = buttons[index];
    if (typeof button === "boolean") { if (button) pressed.push(index); continue; }
    if (typeof button !== "object" || button === null || !("pressed" in button) || typeof button.pressed !== "boolean") return null;
    if ("value" in button && (typeof button.value !== "number" || !Number.isFinite(button.value) || button.value < 0 || button.value > 1)) return null;
    if (button.pressed) pressed.push(index);
  }
  return pressed;
}
