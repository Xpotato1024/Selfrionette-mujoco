"""Runtime composition root."""

from __future__ import annotations

from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.dry_run import run_replay_mujoco_dry_run
from selfrionette.runtime.live_viewer_smoke import run_live_viewer_smoke
from selfrionette.runtime.evaluation import (
    RuntimeForwardKinematicsEvaluation,
    evaluate_fk_endpoint_from_joint_command,
    evaluate_fk_endpoint_from_qpos,
)
from selfrionette.runtime.mujoco_pipeline import build_mujoco_pipeline
from selfrionette.runtime.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.runtime.websocket_publisher_runner import run_replay_mujoco_websocket_publisher
from selfrionette.runtime.pipeline import RuntimePipeline, build_noop_pipeline

__all__ = [
    "RuntimeConfig",
    "RuntimePipeline",
    "RuntimeForwardKinematicsEvaluation",
    "build_concrete_mujoco_pipeline",
    "build_noop_pipeline",
    "build_mujoco_pipeline",
    "evaluate_fk_endpoint_from_joint_command",
    "evaluate_fk_endpoint_from_qpos",
    "build_replay_mujoco_pipeline",
    "run_replay_mujoco_dry_run",
    "run_live_viewer_smoke",
    "run_replay_mujoco_websocket_publisher",
]
