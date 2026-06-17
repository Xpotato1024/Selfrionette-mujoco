import type { Vector3 } from "../types/transportPayload.js";

export function formatVector3(vector: Vector3 | null): string {
  if (vector === null) {
    return "absent";
  }

  const formatComponent = (value: number): string => {
    const rounded = Math.round(value * 1_000_000) / 1_000_000;
    return Number.isInteger(rounded) ? String(rounded) : String(rounded).replace(/0+$/, "").replace(/\.$/, "");
  };

  return `[${formatComponent(vector[0])}, ${formatComponent(vector[1])}, ${formatComponent(vector[2])}]`;
}

export function formatCount(value: number, noun: string): string {
  return `${value} ${noun}${value === 1 ? "" : "s"}`;
}

