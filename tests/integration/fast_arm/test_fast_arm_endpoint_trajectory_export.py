from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "diagnostics" / "fast_arm" / "plot_fast_arm_endpoint_trajectory_log.py"


def _load_plot_module():
    spec = importlib.util.spec_from_file_location("plot_fast_arm_endpoint_trajectory_log", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, *, include_error_norm: bool = True) -> Path:
    headers = [
        "step",
        "time_s",
        "command_axis",
        "command_label",
        "target_x_m",
        "target_y_m",
        "target_z_m",
        "tip_x_m",
        "tip_y_m",
        "tip_z_m",
        "error_norm_m",
        "status",
        "reason",
    ]
    if not include_error_norm:
        headers.remove("error_norm_m")

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(headers)]
    row_one = [
        "1",
        "0.0",
        "z",
        "+z",
        "0.0",
        "0.0",
        "0.001",
        "0.0",
        "0.0",
        "0.0005",
        "0.0005",
        "pass",
        "aligned",
    ]
    row_two = [
        "2",
        "0.1",
        "z",
        "+z",
        "0.0",
        "0.0",
        "0.002",
        "0.0",
        "0.0",
        "0.001",
        "0.001",
        "pass",
        "aligned",
    ]
    if not include_error_norm:
        row_one.pop(10)
        row_two.pop(10)
    lines.append(",".join(row_one))
    lines.append(",".join(row_two))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_plot_script_smoke_creates_png(tmp_path: Path) -> None:
    plot_module = _load_plot_module()
    input_path = _write_csv(tmp_path / "input.csv")
    output_path = tmp_path / "plots" / "trajectory.png"

    exported = plot_module.render_fast_arm_endpoint_trajectory_log(
        input_path=input_path,
        output_path=output_path,
        axis="z",
    )

    assert exported == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_script_missing_required_columns_fails_clear(tmp_path: Path) -> None:
    plot_module = _load_plot_module()
    input_path = _write_csv(tmp_path / "missing.csv", include_error_norm=False)
    output_path = tmp_path / "trajectory.png"

    try:
        plot_module.render_fast_arm_endpoint_trajectory_log(
            input_path=input_path,
            output_path=output_path,
            axis="z",
        )
    except ValueError as exc:
        message = str(exc)
        assert "error_norm_m" in message
        assert "missing required CSV columns" in message
    else:
        raise AssertionError("expected ValueError for missing CSV columns")
