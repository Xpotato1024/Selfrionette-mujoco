"""Control Mapping Plugin namespace with lazy compatibility exports."""

from __future__ import annotations

import importlib
from typing import Final


_PUBLIC_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN": (
        "selfrionette.plugins.mappings.analog_fixture_mapping",
        "ANALOG_FIXTURE_CONTROL_MAPPING_PLUGIN",
    ),
    "LOADCELL_ENDPOINT_MAPPING_PLUGIN": (
        "selfrionette.plugins.mappings.loadcell_endpoint_mapping",
        "LOADCELL_ENDPOINT_MAPPING_PLUGIN",
    ),
    "REPLAY_CONTROL_MAPPING_PLUGIN": (
        "selfrionette.plugins.mappings.replay_mapping",
        "REPLAY_CONTROL_MAPPING_PLUGIN",
    ),
    "VIEWER_CONTROL_MAPPING_PLUGIN": (
        "selfrionette.plugins.mappings.viewer_keyboard_gamepad_mapping",
        "VIEWER_CONTROL_MAPPING_PLUGIN",
    ),
    "ViewerKeyboardGamepadMappingStrategy": (
        "selfrionette.plugins.mappings.viewer_keyboard_gamepad_mapping",
        "ViewerKeyboardGamepadMappingStrategy",
    ),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _PUBLIC_EXPORTS[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    value = getattr(importlib.import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = list(_PUBLIC_EXPORTS)
