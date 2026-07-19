from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REQUIRED_COLUMNS = (
    "step",
    "time_s",
    "command_axis",
    "target_x_m",
    "target_y_m",
    "target_z_m",
    "tip_x_m",
    "tip_y_m",
    "tip_z_m",
    "error_norm_m",
    "status",
    "reason",
)


def _parse_axis(value: str) -> str:
    if value not in {"x", "y", "z"}:
        raise argparse.ArgumentTypeError("axis must be one of: x, y, z")
    return value


def _load_rows(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in _REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(
                f"{path} is missing required CSV columns: {', '.join(missing)}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} does not contain any trajectory rows")
    return rows, fieldnames


def _to_float(row: dict[str, str], key: str) -> float:
    value = row.get(key)
    if value is None or value == "":
        raise ValueError(f"CSV column {key!r} is empty")
    return float(value)


def _select_axis_rows(
    rows: Sequence[dict[str, str]],
    *,
    axis: str,
) -> tuple[list[dict[str, str]], str]:
    axis_rows = [row for row in rows if row.get("command_axis") == axis]
    if not axis_rows:
        raise ValueError(f"CSV does not contain any rows for axis {axis!r}")

    selected_label = axis_rows[0].get("command_label") or axis
    selected_rows = [
        row
        for row in axis_rows
        if (row.get("command_label") or axis) == selected_label
    ]
    selected_rows.sort(key=lambda row: int(row["step"]))
    return selected_rows, selected_label


def render_fast_arm_endpoint_trajectory_log(
    *,
    input_path: str | Path,
    output_path: str | Path,
    axis: str = "z",
    title: str | None = None,
) -> Path:
    input_file = Path(input_path)
    output_file = Path(output_path)
    rows, _ = _load_rows(input_file)
    selected_rows, selected_label = _select_axis_rows(rows, axis=axis)

    times_s = [_to_float(row, "time_s") for row in selected_rows]
    target_values_m = [_to_float(row, f"target_{axis}_m") for row in selected_rows]
    tip_values_m = [_to_float(row, f"tip_{axis}_m") for row in selected_rows]
    error_norm_values_m = [_to_float(row, "error_norm_m") for row in selected_rows]
    status_values = [row["status"] for row in selected_rows]
    reason_values = [row["reason"] for row in selected_rows]
    final_reason = reason_values[-1]
    final_status = status_values[-1]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    figure, (axis_plot, error_plot) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(9.0, 6.0),
        constrained_layout=True,
    )

    axis_plot.plot(times_s, target_values_m, label=f"target {axis}", linewidth=2.0)
    axis_plot.plot(times_s, tip_values_m, label=f"tip {axis}", linewidth=2.0)
    axis_plot.set_ylabel(f"{axis} position (m)")
    axis_plot.grid(True, alpha=0.25)
    axis_plot.legend(loc="best")

    error_plot.plot(times_s, error_norm_values_m, color="#444444", linewidth=2.0)
    error_plot.set_ylabel("error norm (m)")
    error_plot.set_xlabel("time (s)")
    error_plot.grid(True, alpha=0.25)

    plot_title = title or f"fast_arm endpoint trajectory log ({selected_label})"
    figure.suptitle(f"{plot_title} - {final_status} / {final_reason}")
    figure.savefig(output_file, dpi=180)
    plt.close(figure)
    return output_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot fast_arm endpoint trajectory logs.")
    parser.add_argument("--input", type=Path, required=True, help="trajectory CSV input path")
    parser.add_argument("--output", type=Path, required=True, help="PNG output path")
    parser.add_argument("--axis", type=_parse_axis, default="z", help="axis to plot")
    parser.add_argument("--title", default=None, help="optional plot title")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        render_fast_arm_endpoint_trajectory_log(
            input_path=args.input,
            output_path=args.output,
            axis=args.axis,
            title=args.title,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
