from __future__ import annotations

import ast
from pathlib import Path

import selfrionette.runtime as runtime


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "src" / "selfrionette" / "runtime"
EXPECTED_MODULES = {
    "composition": {
        "config",
        "concrete_mujoco_pipeline",
        "replay_mujoco_pipeline",
        "robot_bundle",
        "robot_plugin",
        "robot_profile",
        "robot_profile_metadata",
        "robot_resource",
        "robot_provider_adapters",
        "robot_resolution",
        "viewer_robot_declaration",
    },
    "control": {
        "desired_endpoint_resolver",
        "endpoint_target_generator",
        "input_source_selection",
        "input_source_state",
        "input_step_diagnostics",
        "viewer_control_ingress",
        "viewer_motion_policy",
    },
    "evaluation": {"endpoint_metrics", "endpoint_progress", "kinematics", "manifest"},
    "execution": {"input_step_loop", "live_timing", "pipeline"},
    "experiment": {"composition", "contracts", "registry"},
    "runners": {
        "dry_run",
        "live_loadcell",
        "live_viewer_smoke",
        "live_websocket_delivery",
        "loadcell_serial_dry_run",
        "offline_input_smoke",
        "websocket_publisher",
    },
    "safety": {"input_safety", "qpos_feasibility"},
}
RETIRED_FLAT_MODULES = (frozenset().union(*EXPECTED_MODULES.values()) - set(EXPECTED_MODULES)) | {
    "evaluation_manifest",
    "experiment_composition",
    "experiment_contracts",
    "experiment_registry",
    "live_loadcell_runtime_runner",
    "offline_input_runtime_smoke",
    "websocket_publisher_runner",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    return imported


def test_runtime_modules_have_one_responsibility_owner() -> None:
    assert {path.stem for path in RUNTIME_ROOT.glob("*.py")} == {"__init__"}
    assert {
        path.name
        for path in RUNTIME_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    } == set(EXPECTED_MODULES)
    for owner, expected_modules in EXPECTED_MODULES.items():
        actual_modules = {path.stem for path in (RUNTIME_ROOT / owner).glob("*.py")}
        assert actual_modules == {"__init__", *expected_modules}


def test_retired_flat_runtime_imports_have_no_repository_consumers() -> None:
    retired_imports = {f"selfrionette.runtime.{name}" for name in RETIRED_FLAT_MODULES}
    for root in (ROOT / "src", ROOT / "tests", ROOT / "scripts"):
        for path in root.rglob("*.py"):
            assert _imports(path).isdisjoint(retired_imports), path.relative_to(ROOT)


def test_runtime_package_root_is_a_minimal_lazy_facade() -> None:
    assert set(runtime.__all__) == {
        "RuntimeConfig",
        "RuntimePipeline",
        "registered_robot_bundle_ids",
        "registered_robot_runtime_plugin_ids",
        "resolve_robot_bundle",
        "resolve_robot_runtime",
        "resolve_robot_runtime_plugin",
    }
    assert set(runtime._PUBLIC_EXPORTS) == set(runtime.__all__)


def test_experiment_runner_has_one_future_owner() -> None:
    readme = (RUNTIME_ROOT / "README.md").read_text(encoding="utf-8")
    assert "experiment lifecycle / runnerは`experiment/`が所有する" in readme
    assert "`runners/`は既存のoperational smoke / runnerだけを所有する" in readme
