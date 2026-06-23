from __future__ import annotations

import pytest

from selfrionette.input_sources import INPUT_SOURCE_REGISTRY, SUPPORTED_INPUT_SOURCE_NAMES, get_input_source_descriptor


def test_runtime_input_source_registry_exposes_supported_sources() -> None:
    assert SUPPORTED_INPUT_SOURCE_NAMES == ("programmed_target", "replay", "noop")
    assert tuple(INPUT_SOURCE_REGISTRY) == SUPPORTED_INPUT_SOURCE_NAMES


@pytest.mark.parametrize(
    ("source_name", "expected_contract_key", "expected_contract_value"),
    [
        ("programmed_target", "trajectory_name", "sweep_x"),
        ("replay", "preset", "r6-h-p5-default"),
        ("noop", "source_kind", "noop"),
    ],
)
def test_runtime_input_source_registry_initial_metadata_contract(
    source_name: str,
    expected_contract_key: str,
    expected_contract_value: object,
) -> None:
    descriptor = get_input_source_descriptor(source_name)

    assert descriptor.name == source_name
    assert expected_contract_key in descriptor.initial_metadata
    assert descriptor.initial_metadata[expected_contract_key] == expected_contract_value
    assert callable(descriptor.build_frames)


def test_runtime_input_source_registry_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="unsupported input source"):
        get_input_source_descriptor("unknown")
