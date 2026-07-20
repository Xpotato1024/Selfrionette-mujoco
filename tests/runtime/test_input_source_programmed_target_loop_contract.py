from __future__ import annotations

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.runtime.control.input_source_selection import select_runtime_input_source


def test_programmed_target_plugin_factory_honors_loop_parameter() -> None:
    plugin = INPUT_SOURCE_CATALOG.resolve("programmed_target").plugin
    reader = plugin.create_runtime_reader(
        {
            "steps": 1,
            "initial_position_m": (0.0, 0.0, 0.0),
            "preset": "sweep_x",
            "loop": True,
        }
    )

    frames = [reader.read_frame() for _ in range(22)]

    assert frames[0].metadata["frame_index"] == 0
    assert frames[20].metadata["frame_index"] == 20
    assert frames[21] == frames[0]


def test_programmed_target_cli_selection_keeps_loop_disabled() -> None:
    selection = select_runtime_input_source("programmed_target", steps=1)

    assert selection.loop is False
    assert selection.validated_parameters is not None
    assert selection.validated_parameters["loop"] is False
