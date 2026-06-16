from __future__ import annotations

import ast
import json
from pathlib import Path

from selfrionette.runtime import run_replay_mujoco_dry_run


ROOT = Path(__file__).resolve().parents[2]
DRY_RUN_MODULE = ROOT / "src" / "selfrionette" / "runtime" / "dry_run.py"


def test_dry_run_sweep_x_uses_programmed_input_source_metadata() -> None:
    payload = json.loads(run_replay_mujoco_dry_run(steps=1, preset="sweep_x")[0])

    assert payload["metadata"]["source_kind"] == "programmed_target"
    assert payload["metadata"]["trajectory_name"] == "sweep_x"
    assert payload["metadata"]["phase"] == "initial_hold"
    assert payload["metadata"]["preset"] == "sweep_x"
    assert payload["metadata"]["desired_endpoint_m"] == payload["target_position_m"]


def test_dry_run_module_uses_programmed_input_source_and_not_noop_motion_generator() -> None:
    source_text = DRY_RUN_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(DRY_RUN_MODULE))

    assert "build_sweep_x_input_source" in source_text
    assert "NoOpMotionGenerator" not in source_text

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "selfrionette.input_sources":
            imported_names.update(alias.name for alias in node.names)

    assert "build_sweep_x_input_source" in imported_names
