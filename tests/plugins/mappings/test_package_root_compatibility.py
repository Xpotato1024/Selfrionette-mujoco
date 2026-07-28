from __future__ import annotations

import importlib
import subprocess
import sys

import pytest

from selfrionette.plugins import mappings
from selfrionette.plugins.control_mapping_discovery import (
    discover_production_control_mapping_plugins,
)


BASELINE_ROOT_EXPORTS = {
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


def test_package_root_preserves_baseline_exports_from_canonical_owners() -> None:
    assert set(mappings.__all__) == set(BASELINE_ROOT_EXPORTS)
    for export_name, (module_name, attribute_name) in BASELINE_ROOT_EXPORTS.items():
        canonical_owner = importlib.import_module(module_name)
        assert getattr(mappings, export_name) is getattr(
            canonical_owner, attribute_name
        )


def test_package_root_rejects_unknown_exports() -> None:
    with pytest.raises(
        AttributeError,
        match="has no attribute 'UNKNOWN_CONTROL_MAPPING_PLUGIN'",
    ):
        getattr(mappings, "UNKNOWN_CONTROL_MAPPING_PLUGIN")


def test_package_root_loads_only_the_requested_canonical_owner() -> None:
    script = """
import sys

from selfrionette.plugins import mappings

implementation_modules = {
    "selfrionette.plugins.mappings.analog_fixture_mapping.implementation",
    "selfrionette.plugins.mappings.loadcell_endpoint_mapping.implementation",
    "selfrionette.plugins.mappings.replay_mapping.implementation",
    "selfrionette.plugins.mappings.viewer_keyboard_gamepad_mapping.implementation",
}
assert implementation_modules.isdisjoint(sys.modules)

assert mappings.REPLAY_CONTROL_MAPPING_PLUGIN.identity.canonical_id == (
    "replay_mapping/v1"
)
assert (
    "selfrionette.plugins.mappings.replay_mapping.implementation"
    in sys.modules
)
assert implementation_modules - {
    "selfrionette.plugins.mappings.replay_mapping.implementation"
} == (implementation_modules - set(sys.modules))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_production_discovery_does_not_read_compatibility_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailOnCompatibilityExportRead(dict[str, tuple[str, str]]):
        def __getitem__(self, key: str) -> tuple[str, str]:
            raise AssertionError(f"compatibility export was read: {key}")

    monkeypatch.setattr(
        mappings,
        "_PUBLIC_EXPORTS",
        FailOnCompatibilityExportRead(),
    )

    registry = discover_production_control_mapping_plugins()

    assert registry.ids == (
        "analog_fixture_mapping",
        "loadcell_endpoint_mapping",
        "replay_mapping",
        "viewer_keyboard_gamepad_mapping",
    )
