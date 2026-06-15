from __future__ import annotations

import ast
import json
from pathlib import Path

import selfrionette.runtime.dry_run as dry_run_module
import selfrionette.runtime.websocket_publisher_runner as websocket_runner_module
from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.input_sources import ReplayInputSource
from selfrionette.motion import TargetToJointMotionGenerator
from selfrionette.input_interpreters import NoOpInputInterpreter
from selfrionette.input_sources import StaticInputSource
from selfrionette.mujoco_backend import HeadlessMuJoCoSimulator
from selfrionette.mujoco_backend import NoOpMuJoCoSimulator
from selfrionette.runtime import build_concrete_mujoco_pipeline, run_replay_mujoco_dry_run, run_replay_mujoco_websocket_publisher
from selfrionette.schemas import MotionCommand, MuJoCoState
from selfrionette.transport import NoOpStatePublisher, WebSocketStatePublisher


ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_RUNTIME_MODULES = (
    ROOT / "src" / "selfrionette" / "runtime" / "concrete_mujoco_pipeline.py",
    ROOT / "src" / "selfrionette" / "runtime" / "websocket_publisher_runner.py",
)
FORBIDDEN_RUNTIME_SYMBOLS = (
    "StaticInputSource",
    "NoOpInputInterpreter",
    "NoOpMotionGenerator",
    "NoOpMuJoCoSimulator",
    "NoOpStatePublisher",
    "ZeroForwardKinematicsSolver",
    "ZeroInverseKinematicsSolver",
    "build_noop_pipeline()",
)


class RecordingPublisher:
    def __init__(self) -> None:
        self.states: list[MuJoCoState] = []

    async def publish(self, state: MuJoCoState) -> None:
        self.states.append(state)


class _ForbiddenNoOpMotionGenerator:
    def __init__(self, *args, **kwargs) -> None:
        raise AssertionError("default dry-run path must not construct NoOpMotionGenerator")


class _RecordingNoOpMotionGenerator:
    instances = 0
    updates = 0

    def __init__(self) -> None:
        type(self).instances += 1

    def update(self, intent, dt_s: float) -> MotionCommand:
        type(self).updates += 1
        return MotionCommand(
            timestamp_s=intent.timestamp_s,
            target=None,
            joint=None,
            metadata=dict(intent.metadata),
        )


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
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert not any(module.endswith(".stubs") for module in imported_modules)

        source = path.read_text(encoding="utf-8")
        offending = [symbol for symbol in FORBIDDEN_RUNTIME_SYMBOLS if symbol in source]
        assert not offending, f"{path.relative_to(ROOT)} references forbidden stub symbols: {offending}"


def test_build_concrete_mujoco_pipeline_uses_concrete_components() -> None:
    publisher = RecordingPublisher()
    pipeline = build_concrete_mujoco_pipeline(publisher=publisher)

    assert isinstance(pipeline.input_source, ReplayInputSource)
    assert not isinstance(pipeline.input_source, StaticInputSource)
    assert isinstance(pipeline.input_interpreter, ReplayInputInterpreter)
    assert not isinstance(pipeline.input_interpreter, NoOpInputInterpreter)
    assert isinstance(pipeline.motion_generator, TargetToJointMotionGenerator)
    assert isinstance(pipeline.simulator, HeadlessMuJoCoSimulator)
    assert not isinstance(pipeline.simulator, NoOpMuJoCoSimulator)
    assert pipeline.publisher is publisher
    assert not isinstance(pipeline.publisher, NoOpStatePublisher)


def test_run_replay_mujoco_dry_run_default_path_does_not_construct_noop_motion_generator(monkeypatch) -> None:
    monkeypatch.setattr(dry_run_module, "NoOpMotionGenerator", _ForbiddenNoOpMotionGenerator)

    payload = json.loads(run_replay_mujoco_dry_run(steps=1)[0])

    assert payload["qpos"][:4] != [0.0, 0.0, 0.0, 0.0]


def test_run_replay_mujoco_dry_run_sweep_x_path_remains_explicit_compatibility_path(monkeypatch) -> None:
    _RecordingNoOpMotionGenerator.instances = 0
    _RecordingNoOpMotionGenerator.updates = 0
    monkeypatch.setattr(dry_run_module, "NoOpMotionGenerator", _RecordingNoOpMotionGenerator)

    payload = json.loads(run_replay_mujoco_dry_run(steps=1, preset="sweep_x")[0])

    assert _RecordingNoOpMotionGenerator.instances == 1
    assert _RecordingNoOpMotionGenerator.updates == 1
    assert payload["metadata"]["preset"] == "sweep_x"
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
