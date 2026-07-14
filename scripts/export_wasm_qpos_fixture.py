from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from selfrionette.runtime import run_replay_mujoco_dry_run

FIXTURE_MODEL_PATH = "assets/mujoco/fast_arm/scene.xml"
FIXTURE_SOURCE = "python-native-mujoco"
DEFAULT_OUTPUT_PATH = ROOT / "apps" / "mujoco-viewer" / "public" / "fixtures" / "fast_arm_sweep_x_qpos.json"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("steps must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("dt-s must be positive")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the product-owned browser qpos fixture from the native MuJoCo dry-run path."
    )
    parser.add_argument("--preset", choices=("sweep_x",), default="sweep_x", help="deterministic replay preset to export")
    parser.add_argument("--steps", type=_positive_int, default=30, help="number of frames to export")
    parser.add_argument("--dt-s", type=_positive_float, default=1.0 / 60.0, help="backend step duration in seconds")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="output JSON path; defaults to apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json",
    )
    return parser


def _build_fixture(*, preset: str, steps: int, dt_s: float) -> dict[str, object]:
    payload_lines = run_replay_mujoco_dry_run(steps=steps, dt_s=dt_s, preset=preset)
    if not payload_lines:
        raise RuntimeError("backend dry-run did not return any payload frames")

    frames: list[dict[str, object]] = []
    qpos_length: int | None = None
    for line in payload_lines:
        payload = json.loads(line)
        qpos = payload.get("qpos")
        if not isinstance(qpos, list) or not qpos:
            raise RuntimeError("backend payload qpos must be a non-empty list")

        frame_qpos = [float(value) for value in qpos]
        if not all(math.isfinite(value) for value in frame_qpos):
            raise RuntimeError("backend payload qpos must contain only finite numbers")
        if qpos_length is None:
            qpos_length = len(frame_qpos)
        elif len(frame_qpos) != qpos_length:
            raise RuntimeError("backend payload qpos length changed across frames")

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            raise RuntimeError("backend payload metadata must be a JSON object")

        frames.append(
            {
                "frame_index": payload["frame_index"],
                "t_s": payload["time_s"],
                "qpos": frame_qpos,
                "metadata": metadata,
            }
        )

    assert qpos_length is not None
    return {
        "schema_version": 1,
        "source": FIXTURE_SOURCE,
        "model_path": FIXTURE_MODEL_PATH,
        "preset": preset,
        "qpos_length": qpos_length,
        "frames": frames,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    fixture = _build_fixture(preset=args.preset, steps=args.steps, dt_s=args.dt_s)
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(fixture, ensure_ascii=False, indent=2, allow_nan=False))
        stream.write("\n")
    print(f"Wrote qpos fixture to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
