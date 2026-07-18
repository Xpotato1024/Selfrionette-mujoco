from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/reports/implementation/script-inventory-and-retirement.md"
RETIRED_LAUNCHER = "run_mujoco_viewer_dev.py"
EXPECTED_SCRIPTS = {
    "export_wasm_qpos_fixture.py",
    "measure_loadcell_channel_response.ps1",
    "monitor_loadcell_serial.ps1",
    "plot_fast_arm_endpoint_trajectory_log.py",
    "plot_loadcell_vectors.ps1",
    "run_fast_arm_endpoint_motion_sanity.py",
    "run_fast_arm_jacobian_mobility_diagnostics.py",
    "run_fast_arm_neutral_pose_evaluator.py",
    "run_fast_arm_neutral_pose_startup_smoke.py",
    "run_live_loadcell_runtime.py",
    "run_live_viewer_smoke.py",
    "run_loadcell_serial_dry_run.py",
    "run_replay_mujoco_dry_run.py",
    "run_replay_mujoco_websocket_publisher.py",
    "run-browser-viewer-smoke.ps1",
    "validate_github_body_structure.py",
    "validate_markdown_docs.py",
    "view_fast_arm_native_mujoco.py",
}


def test_script_inventory_covers_the_exact_current_directory() -> None:
    current = {path.name for path in (ROOT / "scripts").iterdir() if path.is_file()}
    assert current == EXPECTED_SCRIPTS

    report = INVENTORY.read_text(encoding="utf-8")
    for name in EXPECTED_SCRIPTS | {RETIRED_LAUNCHER}:
        assert f"`{name}`" in report


def test_retired_launcher_has_no_current_consumer() -> None:
    assert not (ROOT / "scripts" / RETIRED_LAUNCHER).exists()

    files = [ROOT / "README.md", ROOT / "docs/README.md"]
    for directory in (
        ROOT / ".github",
        ROOT / "apps",
        ROOT / "docs/operations",
        ROOT / "scripts",
        ROOT / "tests",
    ):
        files.extend(directory.rglob("*"))

    consumers = []
    for path in files:
        if not path.is_file() or path == Path(__file__):
            continue
        if path.suffix not in {".md", ".py", ".ps1", ".yml", ".yaml", ".toml"}:
            continue
        if RETIRED_LAUNCHER in path.read_text(encoding="utf-8"):
            consumers.append(path.relative_to(ROOT).as_posix())
    assert consumers == []


def test_canonical_default_commands_use_the_installable_cli() -> None:
    for relative_path in (
        "README.md",
        "docs/operations/runtime-dry-run.md",
        "docs/operations/websocket-publisher-runner.md",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "uv run selfrionette" in text
