"""Private registration support shared by loadcell source plugins."""

from __future__ import annotations

from collections.abc import Sequence

from selfrionette.plugins.input_sources._loadcell import (
    normalize_loadcell_frame_for_mapping,
)
from selfrionette.plugins.input_source_registration import InputSourcePluginRequest
from selfrionette.runtime.experiment.contracts import VersionedIdentity
from selfrionette.runtime.experiment.input_source import (
    InputSourceMappingAdapterContract,
)
from selfrionette.schemas import RawInputFrame


LOADCELL_MAPPING_INPUT_ADAPTER = InputSourceMappingAdapterContract(
    input_schema=VersionedIdentity("loadcell_vector_sample", 1),
    output_schema=VersionedIdentity("loadcell_normalized_input_intent", 1),
    adapt=normalize_loadcell_frame_for_mapping,
)


def build_loadcell_request(
    *,
    steps: int,
    frames: Sequence[RawInputFrame] | None,
    preset: str | None,
    line_source: Sequence[str] | None = None,
    **_: object,
) -> InputSourcePluginRequest:
    _ = (steps, frames)
    if preset is not None:
        raise ValueError("preset is not supported for loadcell input source")
    if line_source is None:
        raise ValueError("loadcell input source requires injected fixture lines")
    parameters = {"lines": tuple(line_source)}
    return InputSourcePluginRequest(
        parameters=parameters,
        frames=(),
        loop=False,
        initial_metadata={"source_kind": "loadcell_serial"},
    )


__all__ = ["LOADCELL_MAPPING_INPUT_ADAPTER", "build_loadcell_request"]
