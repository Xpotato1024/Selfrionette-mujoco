from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_generic_runtime_files_do_not_import_fast_arm_implementation() -> None:
    runtime = ROOT / "src" / "selfrionette" / "runtime"
    for name in (
        "config.py",
        "pipeline.py",
        "mujoco_pipeline.py",
        "replay_mujoco_pipeline.py",
        "qpos_feasibility.py",
        "robot_plugin.py",
    ):
        source = (runtime / name).read_text(encoding="utf-8")
        assert "fast_arm" not in source.lower(), name
        assert "FastArm" not in source, name

    simulator_source = (
        ROOT / "src" / "selfrionette" / "mujoco_backend" / "simulator.py"
    ).read_text(encoding="utf-8")
    assert "selfrionette.robots.fast_arm" not in simulator_source
    assert "default_fast_arm_scene_path" not in simulator_source
    assert "FAST_ARM_INITIAL_KEYFRAME_NAME" not in simulator_source


def test_generic_viewer_renderer_and_qpos_sync_do_not_embed_fast_arm() -> None:
    viewer = ROOT / "apps" / "mujoco-viewer" / "src" / "wasm-scene"
    for name in ("mujocoSceneRenderer.ts", "mujocoQposSync.ts", "visualStyles.ts"):
        source = (viewer / name).read_text(encoding="utf-8")
        assert "fast_arm" not in source.lower(), name


def test_profile_registries_do_not_use_arbitrary_dynamic_imports() -> None:
    paths = (
        ROOT / "src" / "selfrionette" / "robot_registry.py",
        ROOT / "src" / "selfrionette" / "runtime" / "robot_plugin_registry.py",
        ROOT / "apps" / "mujoco-viewer" / "src" / "robot-profiles" / "registry.ts",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "importlib" not in source
        assert "__import__" not in source
        assert "import(" not in source


def test_runtime_package_root_exports_contract_not_fast_arm_plugin_class() -> None:
    import selfrionette.runtime as runtime

    assert "RobotRuntimePlugin" in runtime.__all__
    assert "resolve_robot_runtime_plugin" in runtime.__all__
    assert "FastArmRuntimePlugin" not in runtime.__all__
    assert not hasattr(runtime, "FastArmRuntimePlugin")
