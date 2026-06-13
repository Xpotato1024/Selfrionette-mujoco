from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from selfrionette.runtime import run_replay_mujoco_dry_run


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic MuJoCo replay dry-run entry.")
    parser.add_argument("--steps", type=_positive_int, default=1, help="number of replay steps to run")
    parser.add_argument("--dt-s", type=_positive_float, default=None, help="optional step duration in seconds")
    parser.add_argument("--output", type=Path, default=None, help="optional NDJSON output path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output = args.output if args.output is not None else sys.stdout
    run_replay_mujoco_dry_run(steps=args.steps, dt_s=args.dt_s, output=output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
