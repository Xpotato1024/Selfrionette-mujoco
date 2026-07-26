"""Legacy keyboard mapping facade.

The canonical implementation lives in ``plugins.mappings.keyboard``. This
module remains import-compatible for existing offline callers and tests.
"""

from selfrionette.plugins.mappings.keyboard import (
    KeyboardBinding,
    KeyboardInputConfig,
    build_default_keyboard_input_config,
    build_keyboard_continuous_velocity_intent,
    build_keyboard_motion_command,
)

__all__ = [
    "KeyboardBinding",
    "KeyboardInputConfig",
    "build_default_keyboard_input_config",
    "build_keyboard_continuous_velocity_intent",
    "build_keyboard_motion_command",
]
