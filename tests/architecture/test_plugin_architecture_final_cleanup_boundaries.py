from __future__ import annotations

import ast
from pathlib import Path

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.catalog import CONTROL_MAPPING_REGISTRY


ROOT = Path(__file__).resolve().parents[2]
PLUGINS = ROOT / "src" / "selfrionette" / "plugins"
SOURCE_ROOT = PLUGINS / "input_sources"
MAPPING_ROOT = PLUGINS / "mappings"


def _string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _concrete_identity_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"PluginSelection", "VersionedIdentity"}
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


def test_final_source_identity_and_mixed_owners_are_retired() -> None:
    assert INPUT_SOURCE_CATALOG.ids == (
        "analog_fixture",
        "noop",
        "programmed_target",
        "replay",
        "selfrionette",
        "viewer",
    )
    for retired in (
        SOURCE_ROOT / "_common.py",
        SOURCE_ROOT / "_loadcell" / "__init__.py",
        SOURCE_ROOT / "loadcell_serial" / "plugin.py",
        SOURCE_ROOT / "loadcell_fixture" / "plugin.py",
    ):
        assert not retired.is_file()
    assert (SOURCE_ROOT / "selfrionette" / "protocol.py").is_file()


def test_plugin_packages_do_not_own_cross_axis_concrete_ids() -> None:
    mapping_ids = set(CONTROL_MAPPING_REGISTRY.ids)
    source_ids = set(INPUT_SOURCE_CATALOG.ids)
    for source_id in source_ids:
        literals = set().union(
            *(_string_literals(path) for path in (SOURCE_ROOT / source_id).rglob("*.py"))
        )
        assert not literals & mapping_ids
    for mapping_id in mapping_ids:
        concrete_identity_names = set().union(
            *(
                _concrete_identity_names(path)
                for path in (MAPPING_ROOT / mapping_id).rglob("*.py")
            )
        )
        assert not concrete_identity_names & source_ids


def test_input_source_packages_do_not_project_mapping_parameters() -> None:
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SOURCE_ROOT.rglob("*.py")
    )
    for mapping_parameter_surface in (
        "viewer_mapping_parameters",
        "mapping_compatibility_parameters",
        "gamepad_speed_m_s",
        "gamepad_deadzone",
        "gamepad_max_delta_m",
        "keyboard_config",
        "operational_deadzone",
    ):
        assert mapping_parameter_surface not in source_text


def test_catalog_order_is_identity_derived_without_plugin_ordinals() -> None:
    registration = (
        PLUGINS / "input_source_registration.py"
    ).read_text(encoding="utf-8")
    catalog = (SOURCE_ROOT / "catalog.py").read_text(encoding="utf-8")
    plugin_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SOURCE_ROOT.glob("*/plugin.py")
    )
    for retired_field in ("catalog_order", "generic_cli_order"):
        assert retired_field not in registration
        assert retired_field not in catalog
        assert retired_field not in plugin_sources
    assert "item.plugin.identity.canonical_id" in catalog


def test_temporary_plugin_compatibility_facades_are_absent() -> None:
    retired = (
        SOURCE_ROOT / "registration.py",
        MAPPING_ROOT / "analog_fixture.py",
        MAPPING_ROOT / "continuous_endpoint_velocity.py",
        MAPPING_ROOT / "keyboard.py",
        MAPPING_ROOT / "loadcell.py",
        MAPPING_ROOT / "replay.py",
        MAPPING_ROOT / "viewer.py",
    )
    assert all(not path.is_file() for path in retired)
    mapping_root = (MAPPING_ROOT / "__init__.py").read_text(encoding="utf-8")
    assert "_PUBLIC_EXPORTS" not in mapping_root
    assert "__getattr__" not in mapping_root
    source_catalog = (SOURCE_ROOT / "catalog.py").read_text(encoding="utf-8")
    runtime_contract = (
        ROOT / "src" / "selfrionette" / "runtime" / "experiment" / "input_source.py"
    ).read_text(encoding="utf-8")
    for retired_name in (
        "INPUT_SOURCE_PLUGIN_REGISTRY",
        "SUPPORTED_INPUT_SOURCE_NAMES",
        "InputSourceMappingAdapter =",
        "SourceMode =",
        "def create_reader(",
        "def produced_sample_schema_identity(",
    ):
        assert retired_name not in source_catalog
        assert retired_name not in runtime_contract


def test_first_party_package_basename_matches_logical_identity() -> None:
    for registration in INPUT_SOURCE_CATALOG.registrations:
        identity = registration.plugin.identity.name
        assert (SOURCE_ROOT / identity / "plugin.py").is_file()
    for identity in CONTROL_MAPPING_REGISTRY.ids:
        assert (MAPPING_ROOT / identity / "plugin.py").is_file()


def test_selfrionette_backend_and_normalization_boundaries_are_explicit() -> None:
    source = (SOURCE_ROOT / "selfrionette" / "protocol.py").read_text(
        encoding="utf-8"
    )
    mapping = (
        MAPPING_ROOT / "loadcell_endpoint_mapping" / "implementation.py"
    ).read_text(encoding="utf-8")
    reader = (SOURCE_ROOT / "selfrionette" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "operational_deadzone" not in source
    assert "operational_deadzone" in mapping
    assert "import serial" in reader
    assert reader.index("def start(") < reader.index("import serial")


def test_test_fixtures_are_not_discoverable_production_sources() -> None:
    assert "fixture" not in INPUT_SOURCE_CATALOG.ids
    assert "test_dummy_input_source" not in INPUT_SOURCE_CATALOG.ids


def test_mapping_default_resource_is_package_owned() -> None:
    package_resource = (
        MAPPING_ROOT
        / "viewer_keyboard_gamepad_mapping"
        / "resources"
        / "keyboard_default.json"
    )
    assert package_resource.is_file()
    assert not (ROOT / "configs" / "input" / "keyboard_default.json").exists()


def test_generic_runtime_uses_typed_health_and_lifecycle_contracts() -> None:
    generic_runtime = "\n".join(
        (
            (
                ROOT
                / "src"
                / "selfrionette"
                / "runtime"
                / "execution"
                / "input_step_loop.py"
            ).read_text(encoding="utf-8"),
            (
                ROOT
                / "src"
                / "selfrionette"
                / "runtime"
                / "runners"
                / "live_selfrionette.py"
            ).read_text(encoding="utf-8"),
        )
    )
    for migration_duck_surface in (
        'getattr(reader, "start"',
        'getattr(reader, "close"',
        'getattr(source, "start"',
        'getattr(source, "close"',
        'getattr(plan.pipeline.input_source, "current_health"',
    ):
        assert migration_duck_surface not in generic_runtime
    assert "isinstance(reader, ManagedInputSource)" in generic_runtime
    assert "plan.pipeline.input_source.current_health()" in generic_runtime


def test_current_device_facing_surfaces_use_selfrionette_identity() -> None:
    runners = ROOT / "src" / "selfrionette" / "runtime" / "runners"
    hardware = ROOT / "scripts" / "hardware"
    operations = ROOT / "docs" / "operations"

    assert (runners / "live_selfrionette.py").is_file()
    assert (runners / "selfrionette_serial_dry_run.py").is_file()
    assert not (runners / "live_loadcell.py").exists()
    assert not (runners / "loadcell_serial_dry_run.py").exists()

    assert (
        hardware / "selfrionette" / "run_live_selfrionette_runtime.py"
    ).is_file()
    assert (
        hardware / "selfrionette" / "run_selfrionette_serial_dry_run.py"
    ).is_file()
    assert (
        hardware / "selfrionette" / "monitor_selfrionette_serial.ps1"
    ).is_file()
    assert not (hardware / "loadcell").exists()

    canonical_docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in operations.rglob("*.md")
        if "status: canonical" in path.read_text(encoding="utf-8")
        or "status: supporting" in path.read_text(encoding="utf-8")
    )
    for retired_current_surface in (
        "scripts/hardware/loadcell/",
        "run_live_loadcell_runtime.py",
        "run_loadcell_serial_dry_run.py",
        "runtime.runners.live_loadcell",
        "runtime.runners.loadcell_serial_dry_run",
    ):
        assert retired_current_surface not in canonical_docs

    assert "selfrionette/v1" in (
        SOURCE_ROOT / "selfrionette" / "plugin.py"
    ).read_text(encoding="utf-8")
    assert "loadcell_vector_sample" in (
        SOURCE_ROOT / "selfrionette" / "plugin.py"
    ).read_text(encoding="utf-8")
