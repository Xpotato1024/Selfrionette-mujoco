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
from selfrionette.runtime.desired_endpoint_resolver import (
    ResolvedDesiredEndpoint,
    resolve_desired_endpoint_from_motion_command,
)
from selfrionette.runtime.endpoint_metrics import (
    EndpointEvaluationStatePublisher,
    RuntimeEndpointEvaluationMetrics,
    build_endpoint_evaluation_state_publisher,
    build_runtime_endpoint_evaluation_payload,
    build_runtime_endpoint_evaluation_payload_from_state,
    build_runtime_endpoint_evaluation_metrics,
    compute_error_norm_m,
    compute_vector_error_m,
    runtime_endpoint_evaluation_metrics_to_payload,
)
from selfrionette.runtime.offline_input_runtime_smoke import (
    OfflineInputRuntimeSmokeResult,
    run_offline_input_runtime_stepping_smoke,
)
from selfrionette.runtime.live_loadcell_runtime_runner import (
    DEFAULT_LIVE_LOADCELL_BAUD_RATE,
    DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M,
    DEFAULT_LIVE_LOADCELL_MAX_FRAMES,
    DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME,
    LiveLoadcellRuntimeRunnerConfig,
    run_live_loadcell_runtime_runner,
)
from selfrionette.mujoco_backend.endpoint_extraction import (
    RuntimeMuJoCoSiteEndpointEvaluation,
    extract_fast_arm_end_effector_site_endpoint,
    extract_fast_arm_end_effector_site_endpoint_from_state,
    extract_fast_arm_tip_site_endpoint,
    extract_fast_arm_tip_site_endpoint_from_state,
    extract_mujoco_site_endpoint,
    extract_mujoco_site_endpoint_from_state,
)
from selfrionette.runtime.mujoco_pipeline import build_mujoco_pipeline
from selfrionette.runtime.replay_mujoco_pipeline import build_replay_mujoco_pipeline
from selfrionette.runtime.websocket_publisher_runner import run_replay_mujoco_websocket_publisher
from selfrionette.runtime.pipeline import RuntimePipeline, build_noop_pipeline

__all__ = [
    "RuntimeConfig",
    "RuntimePipeline",
    "RuntimeForwardKinematicsEvaluation",
    "RuntimeEndpointEvaluationMetrics",
    "EndpointEvaluationStatePublisher",
    "DEFAULT_LIVE_LOADCELL_BAUD_RATE",
    "DEFAULT_LIVE_LOADCELL_CURRENT_TIP_POSITION_M",
    "DEFAULT_LIVE_LOADCELL_MAX_FRAMES",
    "DEFAULT_LIVE_LOADCELL_STEPS_PER_FRAME",
    "LiveLoadcellRuntimeRunnerConfig",
    "ResolvedDesiredEndpoint",
    "OfflineInputRuntimeSmokeResult",
    "RuntimeMuJoCoSiteEndpointEvaluation",
    "build_concrete_mujoco_pipeline",
    "build_endpoint_evaluation_state_publisher",
    "build_runtime_endpoint_evaluation_payload",
    "build_runtime_endpoint_evaluation_payload_from_state",
    "build_runtime_endpoint_evaluation_metrics",
    "build_noop_pipeline",
    "build_mujoco_pipeline",
    "compute_error_norm_m",
    "compute_vector_error_m",
    "extract_fast_arm_end_effector_site_endpoint",
    "extract_fast_arm_end_effector_site_endpoint_from_state",
    "extract_fast_arm_tip_site_endpoint",
    "extract_fast_arm_tip_site_endpoint_from_state",
    "evaluate_fk_endpoint_from_joint_command",
    "evaluate_fk_endpoint_from_qpos",
    "extract_mujoco_site_endpoint",
    "extract_mujoco_site_endpoint_from_state",
    "resolve_desired_endpoint_from_motion_command",
    "runtime_endpoint_evaluation_metrics_to_payload",
    "build_replay_mujoco_pipeline",
    "run_replay_mujoco_dry_run",
    "run_live_viewer_smoke",
    "run_live_loadcell_runtime_runner",
    "run_offline_input_runtime_stepping_smoke",
    "run_replay_mujoco_websocket_publisher",
]
