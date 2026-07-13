from __future__ import annotations

import asyncio
from pathlib import Path

from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.runtime import (
    RuntimeConfig,
    RuntimePipeline,
    build_mujoco_pipeline,
    build_replay_mujoco_pipeline,
    build_runtime_input_source_step_loop_plan,
    select_runtime_input_source,
)
from selfrionette.runtime.fast_arm_joint_limits import FastArmJointLimitGuard
from selfrionette.runtime.qpos_feasibility import NoOpQposFeasibilityGuard, QposFeasibilityGuard
from selfrionette.schemas import MotionCommand, MuJoCoState, RawInputFrame


MINIMAL_MODEL = """\
<mujoco model="generic_minimal">
  <option gravity="0 0 0"/>
  <worldbody>
    <body name="generic_body">
      <joint name="generic_joint" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01" density="1000"/>
    </body>
  </worldbody>
</mujoco>
"""


def _write_minimal_model(tmp_path: Path) -> Path:
    path = tmp_path / "generic_minimal.xml"
    path.write_text(MINIMAL_MODEL, encoding="utf-8", newline="\n")
    return path


def test_generic_pipeline_accepts_non_fast_arm_model_without_fast_arm_config(tmp_path: Path) -> None:
    model_path = _write_minimal_model(tmp_path)
    config = RuntimeConfig(fast_arm_joint_limits_path=tmp_path / "missing-fast-arm-limits.toml")

    pipeline = build_mujoco_pipeline(model_path=model_path, config=config)

    assert isinstance(pipeline, RuntimePipeline)
    assert isinstance(pipeline.simulator, HeadlessMuJoCoSimulator)
    assert pipeline.qpos_feasibility_guard is None
    state = asyncio.run(pipeline.run_once())

    assert isinstance(state, MuJoCoState)
    assert state.qpos == (0.0,)


def test_generic_replay_pipeline_accepts_non_fast_arm_model_without_fast_arm_validation(tmp_path: Path) -> None:
    model_path = _write_minimal_model(tmp_path)
    pipeline = build_replay_mujoco_pipeline(
        model_path=model_path,
        config=RuntimeConfig(fast_arm_joint_limits_path=tmp_path / "missing-fast-arm-limits.toml"),
        frames=(RawInputFrame(source="replay", timestamp_s=0.0),),
    )

    assert pipeline.qpos_feasibility_guard is None
    state = asyncio.run(pipeline.run_once())

    assert state.qpos == (0.0,)


def test_fast_arm_replay_production_step_loop_explicitly_injects_guard() -> None:
    plan = build_runtime_input_source_step_loop_plan(
        select_runtime_input_source("replay", steps=1),
    )

    assert isinstance(plan.pipeline.qpos_feasibility_guard, FastArmJointLimitGuard)


def test_fast_arm_production_composition_rejects_non_fast_arm_model(tmp_path: Path) -> None:
    model_path = _write_minimal_model(tmp_path)

    from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline

    try:
        build_concrete_mujoco_pipeline(model_path=model_path, publisher=_RecordingPublisher())
    except ValueError as exc:
        assert "joint order" in str(exc) or "missing" in str(exc)
    else:
        raise AssertionError("fast_arm production composition accepted a non-fast-arm model")


def test_generic_feasibility_contract_has_explicit_no_guard_behavior() -> None:
    guard = NoOpQposFeasibilityGuard()

    assert isinstance(guard, QposFeasibilityGuard)
    result = guard.evaluate(
        MotionCommand(timestamp_s=0.0),
        current_qpos_rad=(0.0,),
    )

    assert result.accepted is True
    assert result.action == "accept_no_qpos_candidate"
    assert result.diagnostics == ()


def test_generic_runtime_package_root_excludes_fast_arm_implementation_details() -> None:
    import selfrionette.runtime as runtime

    assert not hasattr(runtime, "FastArmJointLimitConfig")
    assert not hasattr(runtime, "FastArmJointLimitViolation")
    assert not hasattr(runtime, "FastArmQposFeasibilityResult")
    assert hasattr(runtime, "QposFeasibilityGuard")


def test_generic_runtime_modules_do_not_import_fast_arm_limit_implementation() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "selfrionette" / "runtime"
    for relative_path in (
        "pipeline.py",
        "input_safety.py",
        "mujoco_pipeline.py",
        "replay_mujoco_pipeline.py",
    ):
        source = (root / relative_path).read_text(encoding="utf-8")
        assert "fast_arm_joint_limits" not in source


class _RecordingPublisher:
    async def publish(self, state) -> None:  # noqa: ANN001
        _ = state
