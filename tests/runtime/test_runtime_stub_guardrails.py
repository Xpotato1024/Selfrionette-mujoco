from __future__ import annotations

import asyncio
import ast
import json
from pathlib import Path

import selfrionette.runtime.websocket_publisher_runner as websocket_runner_module
from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.input_interpreters.stubs import NoOpInputInterpreter
from selfrionette.input_sources import ReplayInputSource
from selfrionette.input_sources.stubs import StaticInputSource
from selfrionette.kinematics import PlanarTwoLinkInverseKinematicsSolver
from selfrionette.kinematics.stubs import ZeroInverseKinematicsSolver
from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.mujoco_backend.stubs import NoOpMuJoCoSimulator
from selfrionette.runtime import build_concrete_mujoco_pipeline, run_replay_mujoco_dry_run, run_replay_mujoco_websocket_publisher
from selfrionette.schemas import JointCommand, MotionCommand, MuJoCoState
from selfrionette.transport import WebSocketStatePublisher
from selfrionette.transport.stubs import NoOpStatePublisher


ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_RUNTIME_MODULES = (
    ROOT / "src" / "selfrionette" / "runtime" / "concrete_mujoco_pipeline.py",
    ROOT / "src" / "selfrionette" / "runtime" / "replay_mujoco_pipeline.py",
    ROOT / "src" / "selfrionette" / "runtime" / "dry_run.py",
    ROOT / "src" / "selfrionette" / "runtime" / "websocket_publisher_runner.py",
)
COMPATIBILITY_RUNTIME_MODULES = (
    ROOT / "src" / "selfrionette" / "runtime" / "pipeline.py",
    ROOT / "src" / "selfrionette" / "runtime" / "mujoco_pipeline.py",
)
FORBIDDEN_RUNTIME_SYMBOLS = (
    "StaticInputSource",
    "NoOpInputInterpreter",
    "NoOpMotionGenerator",
    "NoOpMuJoCoSimulator",
    "NoOpStatePublisher",
    "ZeroForwardKinematicsSolver",
    "ZeroInverseKinematicsSolver",
)
FORBIDDEN_RUNTIME_MODULES = {
    "selfrionette.input_sources.stubs",
    "selfrionette.input_interpreters.stubs",
    "selfrionette.kinematics.stubs",
    "selfrionette.motion.stubs",
    "selfrionette.mujoco_backend.stubs",
    "selfrionette.transport.stubs",
}

COMPATIBILITY_RUNTIME_STUB_IMPORTS = {
    ROOT / "src" / "selfrionette" / "runtime" / "pipeline.py": {
        "selfrionette.input_interpreters.stubs": {"NoOpInputInterpreter"},
        "selfrionette.input_sources.stubs": {"StaticInputSource"},
        "selfrionette.motion.stubs": {"NoOpMotionGenerator"},
        "selfrionette.mujoco_backend.stubs": {"NoOpMuJoCoSimulator"},
        "selfrionette.transport.stubs": {"NoOpStatePublisher"},
    },
    ROOT / "src" / "selfrionette" / "runtime" / "mujoco_pipeline.py": {
        "selfrionette.input_interpreters.stubs": {"NoOpInputInterpreter"},
        "selfrionette.input_sources.stubs": {"StaticInputSource"},
        "selfrionette.motion.stubs": {"NoOpMotionGenerator"},
        "selfrionette.transport.stubs": {"NoOpStatePublisher"},
    },
}


class RecordingPublisher:
    def __init__(self) -> None:
        self.states: list[MuJoCoState] = []

    async def publish(self, state: MuJoCoState) -> None:
        self.states.append(state)


class _DummyWebSocketPublisherServer:
    def __init__(self, *, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.wait_for_client_calls: list[float | None] = []

    async def __aenter__(self) -> "_DummyWebSocketPublisherServer":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def wait_for_client(self, timeout_s: float | None = None) -> bool:
        self.wait_for_client_calls.append(timeout_s)
        return True


class _DummyPipeline:
    def __init__(self) -> None:
        self.run_once_calls: list[float | None] = []

    async def run_once(self, dt_s: float | None = None) -> object:
        self.run_once_calls.append(dt_s)
        return object()


def test_production_like_runtime_modules_do_not_reference_stub_symbols() -> None:
    for path in PRODUCTION_LIKE_RUNTIME_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert node.module not in FORBIDDEN_RUNTIME_MODULES
                assert not node.module.endswith(".stubs")
                imported_names = {alias.name for alias in node.names}
                assert imported_names.isdisjoint(FORBIDDEN_RUNTIME_SYMBOLS)
            elif isinstance(node, ast.Import):
                imported_names = {alias.name for alias in node.names}
                assert imported_names.isdisjoint(FORBIDDEN_RUNTIME_MODULES)
                assert not any(name.endswith(".stubs") for name in imported_names)

        source = path.read_text(encoding="utf-8")
        offending = [symbol for symbol in FORBIDDEN_RUNTIME_SYMBOLS if symbol in source]
        assert not offending, f"{path.relative_to(ROOT)} references forbidden stub symbols: {offending}"


def test_compatibility_runtime_modules_use_stub_namespace_explicitly() -> None:
    for path in COMPATIBILITY_RUNTIME_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_stub_modules: dict[str, set[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                if node.module.endswith(".stubs"):
                    imported_stub_modules[node.module] = {alias.name for alias in node.names}

        assert imported_stub_modules == COMPATIBILITY_RUNTIME_STUB_IMPORTS[path]


def test_build_concrete_mujoco_pipeline_uses_concrete_components() -> None:
    publisher = RecordingPublisher()
    pipeline = build_concrete_mujoco_pipeline(publisher=publisher)

    assert isinstance(pipeline.input_source, ReplayInputSource)
    assert not isinstance(pipeline.input_source, StaticInputSource)
    assert isinstance(pipeline.input_interpreter, ReplayInputInterpreter)
    assert not isinstance(pipeline.input_interpreter, NoOpInputInterpreter)
    assert isinstance(pipeline.motion_generator, TargetToJointMotionGenerator)
    assert isinstance(pipeline.motion_generator._ik_solver, PlanarTwoLinkInverseKinematicsSolver)
    assert not isinstance(pipeline.motion_generator._ik_solver, ZeroInverseKinematicsSolver)
    assert isinstance(pipeline.simulator, HeadlessMuJoCoSimulator)
    assert not isinstance(pipeline.simulator, NoOpMuJoCoSimulator)
    assert pipeline.publisher is publisher
    assert not isinstance(pipeline.publisher, NoOpStatePublisher)


def test_build_concrete_mujoco_pipeline_emits_non_empty_joint_command_and_padded_qpos() -> None:
    publisher = RecordingPublisher()
    command_pipeline = build_concrete_mujoco_pipeline(publisher=publisher)
    frame = command_pipeline.input_source.read_frame()
    intent = command_pipeline.input_interpreter.interpret(frame)
    command = command_pipeline.motion_generator.update(intent, dt_s=1.0 / 60.0)

    state_pipeline = build_concrete_mujoco_pipeline(publisher=publisher)
    state = asyncio.run(state_pipeline.run_once())

    assert command.joint is not None
    assert command.joint != JointCommand()
    assert command.joint.joint_angles_rad != ()
    assert len(command.joint.joint_angles_rad) == 4
    assert command.joint.joint_angles_rad[:2] != (0.0, 0.0)
    assert state.qpos[:4] == command.joint.joint_angles_rad


def test_run_replay_mujoco_dry_run_default_path_uses_concrete_pipeline() -> None:
    payload = json.loads(run_replay_mujoco_dry_run(steps=1)[0])

    assert payload["qpos"][:4] != [0.0, 0.0, 0.0, 0.0]
    assert payload["version"] == 0


def test_run_replay_mujoco_dry_run_sweep_x_path_remains_explicit_compatibility_path() -> None:
    payload = json.loads(run_replay_mujoco_dry_run(steps=1, preset="sweep_x")[0])

    assert payload["metadata"]["preset"] == "sweep_x"
    assert payload["metadata"]["source_kind"] == "programmed_target"
    assert payload["metadata"]["trajectory_name"] == "sweep_x"
    assert payload["metadata"]["phase"] == "initial_hold"
    assert payload["metadata"]["desired_endpoint_m"] == payload["target_position_m"]


def test_run_replay_mujoco_websocket_publisher_uses_websocket_state_publisher(monkeypatch) -> None:
    captured: dict[str, object] = {}
    dummy_pipeline = _DummyPipeline()

    def fake_build_concrete_mujoco_pipeline(*, publisher, **kwargs):
        captured["publisher"] = publisher
        return dummy_pipeline

    monkeypatch.setattr(websocket_runner_module, "WebSocketPublisherServer", _DummyWebSocketPublisherServer)
    monkeypatch.setattr(websocket_runner_module, "build_concrete_mujoco_pipeline", fake_build_concrete_mujoco_pipeline)

    run_replay_mujoco_websocket_publisher(
        host="127.0.0.1",
        port=8766,
        steps=2,
        dt_s=1.0 / 60.0,
        interval_s=0.0,
        grace_period_s=0.0,
    )

    assert isinstance(captured["publisher"], WebSocketStatePublisher)
    assert dummy_pipeline.run_once_calls == [1.0 / 60.0, 1.0 / 60.0]
