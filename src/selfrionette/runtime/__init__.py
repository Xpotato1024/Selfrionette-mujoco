"""Runtime composition root."""

from __future__ import annotations

from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.concrete_mujoco_pipeline import build_concrete_mujoco_pipeline
from selfrionette.runtime.dry_run import run_replay_mujoco_dry_run
from selfrionette.runtime.input_source_selection import (
    RuntimeInputSourceSelection,
    SUPPORTED_INPUT_SOURCE_NAMES as SUPPORTED_RUNTIME_INPUT_SOURCE_NAMES,
    select_runtime_input_source,
)
from selfrionette.runtime.input_step_loop import (
    RuntimeInputSourceStepLoopPlan,
    RuntimeInputSourceStepLoopRecord,
    build_runtime_input_source_step_loop_plan,
    run_runtime_input_source_step_loop,
)
from selfrionette.runtime.live_viewer_smoke import run_live_viewer_smoke
from selfrionette.runtime.evaluation import (
    RuntimeForwardKinematicsEvaluation,
    evaluate_fk_endpoint_from_joint_command,
    evaluate_fk_endpoint_from_qpos,
)
from selfrionette.runtime.input_source_state import (
    RuntimeInputSourceState,
    annotate_raw_input_frame,
    annotate_runtime_input_source_metadata,
    build_runtime_input_source_state,
    build_runtime_input_source_state_from_metadata,
    runtime_input_source_state_to_metadata,
)
from selfrionette.runtime.input_safety import (
    DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS,
    RuntimeInputSafetyResult,
    build_runtime_input_safety_result,
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
from selfrionette.runtime.endpoint_motion_sanity import (
    FastArmEndpointTrajectoryDiagnostics,
    FastArmEndpointTrajectoryStepRecord,
    FastArmEndpointTrajectorySummary,
    FastArmEndpointMotionSanityResult,
    FastArmLocalJacobianColumn,
    FastArmLocalJacobianPoseDiagnostics,
    FastArmJointAxisPerturbationResult,
    run_fast_arm_endpoint_trajectory_diagnostics,
    run_fast_arm_joint_axis_mapping_diagnostics,
    run_fast_arm_local_jacobian_diagnostics,
    run_fast_arm_endpoint_motion_sanity,
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
from selfrionette.runtime.viewer_control_ingress import (
    build_viewer_input_source,
    ingest_viewer_control_message,
    ingest_viewer_control_message_json,
)
from selfrionette.runtime.websocket_publisher_runner import run_replay_mujoco_websocket_publisher
from selfrionette.runtime.pipeline import RuntimePipeline, build_noop_pipeline

__all__ = [
    "RuntimeConfig",
    "RuntimePipeline",
    "RuntimeInputSourceSelection",
    "RuntimeInputSourceState",
    "RuntimeInputSafetyResult",
    "RuntimeInputSourceStepLoopPlan",
    "RuntimeInputSourceStepLoopRecord",
    "DEFAULT_RUNTIME_INPUT_COMMAND_TIMEOUT_MS",
    "RuntimeForwardKinematicsEvaluation",
    "RuntimeEndpointEvaluationMetrics",
    "FastArmEndpointTrajectoryDiagnostics",
    "FastArmEndpointTrajectoryStepRecord",
    "FastArmEndpointTrajectorySummary",
    "FastArmEndpointMotionSanityResult",
    "FastArmLocalJacobianColumn",
    "FastArmLocalJacobianPoseDiagnostics",
    "FastArmJointAxisPerturbationResult",
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
    "run_fast_arm_endpoint_trajectory_diagnostics",
    "run_fast_arm_joint_axis_mapping_diagnostics",
    "run_fast_arm_local_jacobian_diagnostics",
    "run_fast_arm_endpoint_motion_sanity",
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
    "annotate_raw_input_frame",
    "annotate_runtime_input_source_metadata",
    "build_runtime_input_source_state",
    "build_runtime_input_source_state_from_metadata",
    "build_runtime_input_safety_result",
    "runtime_endpoint_evaluation_metrics_to_payload",
    "runtime_input_source_state_to_metadata",
    "SUPPORTED_RUNTIME_INPUT_SOURCE_NAMES",
    "select_runtime_input_source",
    "build_runtime_input_source_step_loop_plan",
    "run_runtime_input_source_step_loop",
    "build_replay_mujoco_pipeline",
    "build_viewer_input_source",
    "run_replay_mujoco_dry_run",
    "ingest_viewer_control_message",
    "ingest_viewer_control_message_json",
    "run_live_viewer_smoke",
    "run_live_loadcell_runtime_runner",
    "run_offline_input_runtime_stepping_smoke",
    "run_replay_mujoco_websocket_publisher",
]
