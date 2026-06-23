from __future__ import annotations

from selfrionette.input_sources.keyboard import (
    KeyboardBinding,
    KeyboardInputConfig,
    build_default_keyboard_input_config,
    build_keyboard_motion_command,
)
from selfrionette.input_sources.base import InputSource
from selfrionette.input_sources.registry import (
    INPUT_SOURCE_REGISTRY,
    InputSourceDescriptor,
    SUPPORTED_INPUT_SOURCE_NAMES,
    get_input_source_descriptor,
)
from selfrionette.input_sources.programmed_target import ProgrammedTargetInputSource, build_sweep_x_input_source
from selfrionette.input_sources.replay import ReplayInputSource, build_motion_command_from_replay_frame
from selfrionette.loadcell_serial import SerialInputSource

__all__ = [
    "KeyboardBinding",
    "KeyboardInputConfig",
    "build_default_keyboard_input_config",
    "build_keyboard_motion_command",
    "InputSource",
    "INPUT_SOURCE_REGISTRY",
    "InputSourceDescriptor",
    "ProgrammedTargetInputSource",
    "ReplayInputSource",
    "SerialInputSource",
    "SUPPORTED_INPUT_SOURCE_NAMES",
    "build_motion_command_from_replay_frame",
    "build_sweep_x_input_source",
    "get_input_source_descriptor",
]
