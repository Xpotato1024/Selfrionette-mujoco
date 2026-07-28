"""Explicit public Input Source compatibility tests retained until C4."""

from __future__ import annotations

from pathlib import Path

from selfrionette import input_sources
from selfrionette.input_sources.analog_fixture import (
    AnalogFixtureSample as CompatibilityAnalogFixtureSample,
    parse_analog_fixture_sample as compatibility_analog_parse,
)
from selfrionette.input_sources.loadcell_serial import (
    run_loadcell_serial_dry_run_smoke as run_public_loadcell_smoke,
)
from selfrionette.plugins.input_sources._loadcell import (
    LoadcellNormalizationConfig,
    LoadcellNormalizedInputIntentConverter,
    NormalizedLoadcellInputIntent,
    RawLoadcellVectorRecord,
    SerialInputSource,
)
from selfrionette.plugins.input_sources.analog_fixture import (
    AnalogFixtureSample,
    parse_analog_fixture_sample,
)
from selfrionette.plugins.mappings.catalog import resolve_control_mapping_plugin
from selfrionette.plugins.mappings.loadcell import (
    build_r7_a_lite_smoke_endpoint_mapping_config,
)
from selfrionette.runtime.experiment.contracts import PluginSelection
from selfrionette.runtime.runners.loadcell_serial_dry_run import (
    run_loadcell_serial_dry_run_smoke as run_canonical_loadcell_smoke,
)


FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "r7_a_lite_serial_frames"
)


def test_input_source_package_preserves_serial_source_identity() -> None:
    assert input_sources.SerialInputSource is SerialInputSource
    assert "SerialInputSource" in input_sources.__all__
    assert not hasattr(SerialInputSource, "from_port")
    assert not hasattr(SerialInputSource, "open_port")


def test_old_source_facades_re_export_canonical_source_symbols() -> None:
    assert CompatibilityAnalogFixtureSample is AnalogFixtureSample
    assert compatibility_analog_parse is parse_analog_fixture_sample
    assert (
        input_sources.loadcell_serial.LoadcellNormalizationConfig
        is LoadcellNormalizationConfig
    )
    assert (
        input_sources.loadcell_serial.LoadcellNormalizedInputIntentConverter
        is LoadcellNormalizedInputIntentConverter
    )
    assert (
        input_sources.loadcell_serial.NormalizedLoadcellInputIntent
        is NormalizedLoadcellInputIntent
    )
    assert (
        input_sources.loadcell_serial.RawLoadcellVectorRecord
        is RawLoadcellVectorRecord
    )


def test_public_loadcell_mapping_none_behavior_matches_canonical_plugin() -> None:
    endpoint_config = build_r7_a_lite_smoke_endpoint_mapping_config(
        gain_m=1.0,
        max_delta_m=0.03,
    )
    common = {
        "max_vectors": 1,
        "normalization_config": LoadcellNormalizationConfig(
            deadzone=0.0,
            scale=100000.0,
            clamp_abs=1.0,
        ),
        "endpoint_config": endpoint_config,
        "current_tip_position_m": (0.25, 0.5, 0.75),
    }
    lines = FIXTURE_ROOT.joinpath("minimal_valid.txt").read_text(
        encoding="utf-8"
    ).splitlines()

    compatibility_result = run_public_loadcell_smoke(lines, **common)
    canonical_result = run_canonical_loadcell_smoke(
        lines,
        mapping_plugin=resolve_control_mapping_plugin(
            PluginSelection("loadcell_endpoint_mapping", 1)
        ),
        mapping_parameters={
            "mapping_config": endpoint_config,
            "current_tip_position_m": common["current_tip_position_m"],
        },
        **common,
    )

    assert canonical_result == compatibility_result
