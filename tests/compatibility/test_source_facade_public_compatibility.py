"""Explicit source-facade compatibility tests retained until C4."""

from __future__ import annotations

import selfrionette.input_sources as input_sources
import selfrionette.input_sources.programmed_target as compatibility_programmed_target
from selfrionette.input_sources.base import InputSource as CompatibilityInputSource
from selfrionette.input_sources.viewer import (
    DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS as CompatibilityViewerTimeout,
    DEFAULT_VIEWER_SAFE_ENDPOINT_M as CompatibilityViewerEndpoint,
    ViewerInputSource as CompatibilityViewerInputSource,
)
from selfrionette.plugins.input_sources.programmed_target import (
    ProgrammedTargetInputSource,
    build_sweep_x_input_source,
    build_sweep_x_trajectory,
)
from selfrionette.plugins.input_sources.programmed_target import source as canonical_programmed_target
from selfrionette.plugins.input_sources.replay import ReplayInputSource
from selfrionette.plugins.input_sources.viewer import (
    DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS,
    DEFAULT_VIEWER_SAFE_ENDPOINT_M,
    ViewerInputSource,
)
from selfrionette.runtime.experiment.input_source import InputSource
from selfrionette.schemas import RawInputFrame


SWEEP_DEFAULT_NAMES = (
    "DEFAULT_SWEEP_X_INITIAL_POSITION_M",
    "DEFAULT_SWEEP_X_POSITIVE_X_OFFSET_M",
    "DEFAULT_SWEEP_X_DT_S",
    "DEFAULT_SWEEP_X_INITIAL_HOLD_FRAMES",
    "DEFAULT_SWEEP_X_MOVE_FRAMES",
    "DEFAULT_SWEEP_X_SLOW_OR_HOLD_FRAMES",
    "DEFAULT_SWEEP_X_RETURN_FRAMES",
    "DEFAULT_SWEEP_X_FINAL_HOLD_FRAMES",
)


def test_package_root_re_exports_canonical_sources_without_test_doubles() -> None:
    assert input_sources.ProgrammedTargetInputSource is ProgrammedTargetInputSource
    assert input_sources.ReplayInputSource is ReplayInputSource
    assert input_sources.build_sweep_x_input_source is build_sweep_x_input_source
    assert "ProgrammedTargetInputSource" in input_sources.__all__
    assert "build_sweep_x_input_source" in input_sources.__all__
    assert "build_sweep_x_trajectory" not in input_sources.__all__
    assert "StaticInputSource" not in input_sources.__all__
    assert not hasattr(input_sources, "build_sweep_x_trajectory")
    assert not hasattr(input_sources, "StaticInputSource")


def test_programmed_target_module_re_exports_canonical_builder_and_defaults() -> None:
    assert (
        compatibility_programmed_target.ProgrammedTargetInputSource
        is ProgrammedTargetInputSource
    )
    assert (
        compatibility_programmed_target.build_sweep_x_input_source
        is build_sweep_x_input_source
    )
    assert (
        compatibility_programmed_target.build_sweep_x_trajectory
        is build_sweep_x_trajectory
    )
    assert "build_sweep_x_trajectory" in compatibility_programmed_target.__all__
    assert "build_sweep_x_input_source" in compatibility_programmed_target.__all__
    for name in SWEEP_DEFAULT_NAMES:
        compatibility_value = getattr(compatibility_programmed_target, name)
        canonical_value = getattr(canonical_programmed_target, name)
        assert compatibility_value == canonical_value
        assert compatibility_value is canonical_value
        assert name not in compatibility_programmed_target.__all__


def test_viewer_facade_re_exports_canonical_source_and_defaults() -> None:
    assert CompatibilityViewerInputSource is ViewerInputSource
    assert CompatibilityViewerTimeout is DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS
    assert CompatibilityViewerEndpoint is DEFAULT_VIEWER_SAFE_ENDPOINT_M
    assert DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS == 250
    assert DEFAULT_VIEWER_SAFE_ENDPOINT_M == (0.6, 0.0, 0.1)


def test_base_facade_preserves_structural_input_source_identity() -> None:
    class StructuralReader:
        def read_frame(self) -> RawInputFrame:
            return RawInputFrame(source="structural", timestamp_s=0.0)

    reader = StructuralReader()
    assert CompatibilityInputSource is InputSource
    assert isinstance(reader, CompatibilityInputSource)
