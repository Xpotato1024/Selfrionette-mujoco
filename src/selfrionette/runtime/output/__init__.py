"""Physical output permission boundary and later offline trace owners."""

from __future__ import annotations

from selfrionette.runtime.output.permission import (
    evaluate_physical_output_permission,
)
from selfrionette.runtime.output.lifecycle import (
    PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION,
    PhysicalOutputLifecycle,
    PhysicalOutputLifecycleEvent,
    PhysicalOutputLifecycleEventKind,
    PhysicalOutputLifecycleResult,
    PhysicalOutputLifecycleSink,
    PhysicalOutputLifecycleState,
    PhysicalOutputLifecycleTrace,
)
from selfrionette.runtime.output.safety_gate import (
    PHYSICAL_OUTPUT_SAFETY_BINDING_SCHEMA_VERSION,
    PHYSICAL_OUTPUT_SAFETY_EVIDENCE_SCHEMA_VERSION,
    PhysicalOutputSafetyEvaluation,
    PhysicalOutputSafetyStatus,
    PhysicalOutputSafetyTraceEvidence,
    PhysicalOutputSendableRequest,
    bind_physical_output_safety,
    evaluate_and_bind_physical_output_safety,
    validate_physical_output_safety_evaluation,
    validate_physical_output_sendable_request,
)
from selfrionette.runtime.output.trace import (
    PHYSICAL_OUTPUT_TRACE_SCHEMA_VERSION,
    PhysicalOutputRecordingSink,
    PhysicalOutputTrace,
    PhysicalOutputTraceDecisionStatus,
    PhysicalOutputTraceEvent,
    PhysicalOutputTraceEventKind,
    physical_output_traces_equivalent,
    replay_physical_output_trace,
)

__all__ = [
    "PHYSICAL_OUTPUT_SAFETY_BINDING_SCHEMA_VERSION",
    "PHYSICAL_OUTPUT_SAFETY_EVIDENCE_SCHEMA_VERSION",
    "PHYSICAL_OUTPUT_TRACE_SCHEMA_VERSION",
    "PHYSICAL_OUTPUT_LIFECYCLE_SCHEMA_VERSION",
    "PhysicalOutputLifecycle",
    "PhysicalOutputLifecycleEvent",
    "PhysicalOutputLifecycleEventKind",
    "PhysicalOutputLifecycleResult",
    "PhysicalOutputLifecycleSink",
    "PhysicalOutputLifecycleState",
    "PhysicalOutputLifecycleTrace",
    "PhysicalOutputSafetyEvaluation",
    "PhysicalOutputSafetyStatus",
    "PhysicalOutputSafetyTraceEvidence",
    "PhysicalOutputSendableRequest",
    "PhysicalOutputRecordingSink",
    "PhysicalOutputTrace",
    "PhysicalOutputTraceDecisionStatus",
    "PhysicalOutputTraceEvent",
    "PhysicalOutputTraceEventKind",
    "bind_physical_output_safety",
    "evaluate_and_bind_physical_output_safety",
    "evaluate_physical_output_permission",
    "physical_output_traces_equivalent",
    "replay_physical_output_trace",
    "validate_physical_output_safety_evaluation",
    "validate_physical_output_sendable_request",
]
