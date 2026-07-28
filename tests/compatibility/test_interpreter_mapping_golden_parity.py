"""Golden parity for the C3 interpreter-to-versioned-mapping migration."""

from __future__ import annotations

from dataclasses import replace

import pytest

from selfrionette.input_interpreters import ReplayInputInterpreter
from selfrionette.runtime.control.input_source_selection import (
    select_runtime_input_source,
)
from selfrionette.runtime.experiment.contracts import PluginSelection, VersionedIdentity


@pytest.mark.parametrize(
    ("source_name", "produced_schema"),
    (
        ("programmed_target", VersionedIdentity("programmed_target_sample", 1)),
        ("noop", VersionedIdentity("noop_sample", 1)),
    ),
)
def test_identity_adapter_and_replay_mapping_preserve_interpreter_intent(
    source_name: str,
    produced_schema: VersionedIdentity,
) -> None:
    selection = select_runtime_input_source(source_name, steps=1)
    assert selection.control_mapping_selection == PluginSelection("replay_mapping", 1)
    assert selection.control_mapping is not None
    assert selection.mapping_input_adapter is not None
    assert selection.produced_sample_schema == produced_schema
    assert selection.mapping_input_adapter.input_schema == produced_schema
    assert selection.mapping_input_adapter.output_schema == VersionedIdentity(
        "replay_raw_input_frame", 1
    )

    nested_metadata = {"items": ["stable"]}
    frame = replace(
        selection.frames[0],
        metadata={**selection.frames[0].metadata, "nested": nested_metadata},
    )
    adapted = selection.mapping_input_adapter(frame)
    assert adapted is frame

    old_intent = ReplayInputInterpreter().interpret(frame)
    new_intent = selection.control_mapping.strategy.map_input(
        adapted,
        selection.control_mapping_parameters,
    )

    assert new_intent.source == old_intent.source == frame.source
    assert new_intent.timestamp_s == old_intent.timestamp_s == frame.timestamp_s
    assert new_intent.values == old_intent.values == frame.values
    assert new_intent.buttons == old_intent.buttons == frame.buttons
    assert new_intent.metadata == old_intent.metadata == frame.metadata
    assert new_intent.metadata is not old_intent.metadata
    assert new_intent.metadata is not frame.metadata
    assert old_intent.metadata is not frame.metadata
    assert new_intent.metadata["nested"] is nested_metadata
    assert old_intent.metadata["nested"] is nested_metadata
