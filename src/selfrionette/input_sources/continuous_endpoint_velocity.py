from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite, sqrt

from selfrionette.schemas import ContinuousEndpointVelocityIntent


def build_continuous_endpoint_velocity_intent(
    axis_values: Sequence[float],
    *,
    source_kind: str,
    source_timestamp_s: float,
    speed_m_s: float,
    deadzone: float,
    max_delta_m: float,
    control_frame: str = "world",
    source_active: bool = True,
    stale_reason: str | None = None,
    source_diagnostics: Mapping[str, object] | None = None,
    supplemental_axis_values: Sequence[float] = (0.0, 0.0, 0.0),
) -> ContinuousEndpointVelocityIntent:
    """Map already-defined source axes to the common requested-velocity contract."""
    components = tuple(float(component) for component in axis_values)
    if len(components) != 3:
        raise ValueError("axis_values must contain exactly three values")
    if not all(isfinite(component) for component in components):
        raise ValueError("axis_values must contain only finite values")
    supplements = tuple(float(component) for component in supplemental_axis_values)
    if len(supplements) != 3 or not all(isfinite(component) for component in supplements):
        raise ValueError("supplemental_axis_values must contain exactly three finite values")
    for name, value in (("deadzone", deadzone), ("speed_m_s", speed_m_s), ("max_delta_m", max_delta_m)):
        if not isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")

    deadzoned_base = tuple(0.0 if abs(component) <= deadzone else component for component in components)
    base_magnitude = sqrt(sum(component * component for component in deadzoned_base))
    base_was_clamped = base_magnitude > 1.0
    normalized_base = (
        tuple(component / base_magnitude for component in deadzoned_base)
        if base_was_clamped
        else deadzoned_base
    )
    supplemented = tuple(
        base + supplement for base, supplement in zip(normalized_base, supplements, strict=True)
    )
    magnitude = sqrt(sum(component * component for component in supplemented))
    final_was_clamped = magnitude > 1.0
    normalized = (
        tuple(component / magnitude for component in supplemented)
        if final_was_clamped
        else supplemented
    )
    velocity = tuple(component * speed_m_s for component in normalized)
    return ContinuousEndpointVelocityIntent(
        source_kind=source_kind,
        source_timestamp_s=source_timestamp_s,
        axis_values=normalized,
        deadzone_applied_axis_values=deadzoned_base,
        local_endpoint_velocity_m_s=velocity,
        control_frame=control_frame,
        source_active=source_active,
        stale_reason=stale_reason,
        local_endpoint_speed_m_s=speed_m_s,
        local_endpoint_max_delta_m=max_delta_m,
        norm_clamped=base_was_clamped or final_was_clamped,
        source_diagnostics={} if source_diagnostics is None else source_diagnostics,
    )


def build_normalized_analog_fixture_intent(
    axis_values: Sequence[float],
    *,
    source_kind: str = "fixture_analog",
    source_timestamp_s: float,
    speed_m_s: float,
    deadzone: float,
    max_delta_m: float,
    control_frame: str = "world",
    source_active: bool = True,
    stale_reason: str | None = None,
    source_diagnostics: Mapping[str, object] | None = None,
) -> ContinuousEndpointVelocityIntent:
    """Fixture-only extension point; performs no hardware or force mapping."""
    return build_continuous_endpoint_velocity_intent(
        axis_values,
        source_kind=source_kind,
        source_timestamp_s=source_timestamp_s,
        speed_m_s=speed_m_s,
        deadzone=deadzone,
        max_delta_m=max_delta_m,
        control_frame=control_frame,
        source_active=source_active,
        stale_reason=stale_reason,
        source_diagnostics=source_diagnostics,
    )


__all__ = [
    "build_continuous_endpoint_velocity_intent",
    "build_normalized_analog_fixture_intent",
]
