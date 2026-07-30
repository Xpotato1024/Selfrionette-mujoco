export const QPOS_FIXTURE_SCHEMA_VERSION = 1;
export const QPOS_FIXTURE_SOURCE_LABEL = "python-native-mujoco fixture";

/** Python-native MuJoCoが出力した1 frame。t_sはs、qpos orderingはmodel nq順。 */
export interface QposFixtureFrame {
  frame_index: number;
  t_s: number;
  qpos: readonly number[];
  metadata: Record<string, unknown>;
}

/** 明示的offline fixture。live payload欠落時の暗黙fallbackには使用しない。 */
export interface QposFixture {
  schema_version: number;
  source: string;
  model_path: string;
  preset: string;
  qpos_length: number;
  frames: readonly QposFixtureFrame[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toFiniteNumber(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${label} must be a finite number`);
  }

  return value;
}

function toNumberArray(value: unknown, label: string): number[] {
  if (!Array.isArray(value)) {
    throw new Error(`${label} must be an array of numbers`);
  }

  return value.map((item, index) => toFiniteNumber(item, `${label}[${index}]`));
}

function toStringValue(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${label} must be a non-empty string`);
  }

  return value;
}

function toMetadata(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new Error("metadata must be a JSON object");
  }

  return { ...value };
}

function toFrame(value: unknown, frameIndex: number): QposFixtureFrame {
  if (!isRecord(value)) {
    throw new Error(`frame[${frameIndex}] must be a JSON object`);
  }

  return {
    frame_index: toFiniteNumber(value.frame_index, `frame[${frameIndex}].frame_index`),
    t_s: toFiniteNumber(value.t_s, `frame[${frameIndex}].t_s`),
    qpos: toNumberArray(value.qpos, `frame[${frameIndex}].qpos`),
    metadata: toMetadata(value.metadata),
  };
}

/** schema/version/finite値/orderを検証し、unknown shapeを拒否する。 */
export function parseQposFixture(raw: unknown, expectedSchemaVersion = QPOS_FIXTURE_SCHEMA_VERSION): QposFixture {
  if (!isRecord(raw)) {
    throw new Error("fixture must be a JSON object");
  }

  const schemaVersion = toFiniteNumber(raw.schema_version, "schema_version");
  if (schemaVersion !== expectedSchemaVersion) {
    throw new Error(`unsupported schema_version: expected ${expectedSchemaVersion}, got ${schemaVersion}`);
  }

  const framesValue = raw.frames;
  if (!Array.isArray(framesValue) || framesValue.length === 0) {
    throw new Error("frames must be a non-empty array");
  }

  const frames = framesValue.map((frame, index) => toFrame(frame, index));
  const qposLength = toFiniteNumber(raw.qpos_length, "qpos_length");
  if (!Number.isInteger(qposLength) || qposLength < 1) {
    throw new Error("qpos_length must be a positive integer");
  }

  return {
    schema_version: schemaVersion,
    source: toStringValue(raw.source, "source"),
    model_path: toStringValue(raw.model_path, "model_path"),
    preset: toStringValue(raw.preset, "preset"),
    qpos_length: qposLength,
    frames,
  };
}

/** 全frameのqpos長をloaded MuJoCo modelのnqと照合する。 */
export function validateQposFixtureForModel(fixture: QposFixture, modelNq: number): QposFixture {
  if (!Number.isInteger(modelNq) || modelNq < 1) {
    throw new Error("model.nq must be a positive integer");
  }

  if (fixture.qpos_length !== modelNq) {
    throw new Error(`qpos_length mismatch: expected ${modelNq}, got ${fixture.qpos_length}`);
  }

  fixture.frames.forEach((frame, index) => {
    if (frame.qpos.length !== modelNq) {
      throw new Error(`frame[${index}].qpos length mismatch: expected ${modelNq}, got ${frame.qpos.length}`);
    }
  });

  return fixture;
}

export function getFrameByIndex(fixture: QposFixture, frameIndex: number): QposFixtureFrame {
  const frame = fixture.frames[frameIndex];
  if (frame === undefined) {
    throw new Error(`frame index out of range: ${frameIndex}`);
  }

  return frame;
}

export function getNextFrameIndex(currentFrameIndex: number, frameCount: number): number {
  if (frameCount < 1) {
    throw new Error("frameCount must be a positive integer");
  }

  return Math.min(currentFrameIndex + 1, frameCount - 1);
}

export function getPreviousFrameIndex(currentFrameIndex: number): number {
  if (currentFrameIndex < 0) {
    throw new Error("currentFrameIndex must not be negative");
  }

  return Math.max(currentFrameIndex - 1, 0);
}
