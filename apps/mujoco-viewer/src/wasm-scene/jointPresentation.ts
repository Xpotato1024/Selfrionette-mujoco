/** compiled MuJoCoのjoint metadataだけを表示用に投影する。範囲・安全性は推定しない。 */
export type JointDisplayKind = "hinge" | "slide" | "ball" | "free";
export interface JointDisplayLayout {
  readonly qposDimension: number;
  readonly joints: readonly { name: string; kind: JointDisplayKind; address: number; width: number }[];
}
export interface JointReadout {
  name: string;
  kind: JointDisplayKind;
  value: number | null;
  degrees: number | null;
}

export function decodeJointDisplayLayout(names: readonly string[], types: ArrayLike<number>,
  addresses: ArrayLike<number>, qposDimension: number): JointDisplayLayout {
  if (!Number.isSafeInteger(qposDimension) || qposDimension < 1 || !names.length ||
      types.length !== names.length || addresses.length !== names.length ||
      new Set(names).size !== names.length || names.some((name) => typeof name !== "string" || !name.trim())) {
    throw new Error("invalid compiled joint display layout");
  }
  const kinds = ["free", "ball", "slide", "hinge"] as const;
  const widths = [7, 4, 1, 1];
  let nextAddress = 0;
  const joints = names.map((name, index) => {
    const type = types[index];
    const address = addresses[index];
    if (!Number.isInteger(type) || type < 0 || type > 3 || !Number.isInteger(address) || address !== nextAddress) {
      throw new Error("compiled joint type/address mismatch");
    }
    nextAddress += widths[type];
    return { name, kind: kinds[type], address, width: widths[type] };
  });
  if (nextAddress !== qposDimension) throw new Error("compiled joint qpos coverage mismatch");
  return { qposDimension, joints };
}

export function jointReadouts(layout: JointDisplayLayout | null, qpos: readonly number[] | null): JointReadout[] {
  if (layout === null) return [];
  const valid = qpos !== null && qpos.length === layout.qposDimension && qpos.every(Number.isFinite);
  return layout.joints.map((joint) => {
    const scalar = joint.kind === "hinge" || joint.kind === "slide";
    const value = valid && scalar ? qpos[joint.address] : null;
    const converted = joint.kind === "hinge" && value !== null ? value * (180 / Math.PI) : null;
    return { name: joint.name, kind: joint.kind, value,
      degrees: converted !== null && Number.isFinite(converted) ? converted : null };
  });
}

/** 円周方向だけを表示する。元角度や符号付き数値をnormalizeして返さない。 */
export function angleNeedle(radians: number | null): { x: number; y: number } | null {
  if (radians === null || !Number.isFinite(radians)) return null;
  return { x: 42 + 25 * Math.sin(radians), y: 43 - 25 * Math.cos(radians) };
}
