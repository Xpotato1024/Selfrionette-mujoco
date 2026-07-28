"""C3 guards for canonical internal Input Source and Mapping Plugin paths."""

from __future__ import annotations

import ast
from pathlib import Path

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.catalog import (
    CONTROL_MAPPING_PLUGINS,
    CONTROL_MAPPING_REGISTRY,
)


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "selfrionette"
OLD_MODULE_PREFIXES = (
    "selfrionette.input_sources.registry",
    "selfrionette.input_interpreters",
    "selfrionette.input_sources.keyboard",
    "selfrionette.input_sources.continuous_endpoint_velocity",
    "selfrionette.input_sources.analog_fixture",
    "selfrionette.input_sources.loadcell_serial",
    "selfrionette.input_sources.replay",
)
FACADE_SELF_WIRING = {
    SRC / "input_sources" / "__init__.py",
    SRC / "input_interpreters" / "__init__.py",
}
PUBLIC_COMPATIBILITY_TEST_ROOTS = (
    ROOT / "tests" / "compatibility",
    ROOT / "tests" / "input_interpreters",
)
MAPPING_FACADES = (
    SRC / "input_sources" / "keyboard.py",
    SRC / "input_sources" / "continuous_endpoint_velocity.py",
    SRC / "input_sources" / "analog_fixture.py",
    SRC / "input_sources" / "loadcell_serial.py",
    SRC / "input_sources" / "replay.py",
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(path: Path) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            modules.append(module)
            modules.extend(
                f"{module}.{alias.name}"
                for alias in node.names
                if alias.name != "*"
            )
    return tuple(modules)


def _uses_old_module(module: str) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in OLD_MODULE_PREFIXES
    )


def _is_public_compatibility_test(path: Path) -> bool:
    return any(path.is_relative_to(root) for root in PUBLIC_COMPATIBILITY_TEST_ROOTS)


def test_old_imports_are_bounded_to_facade_wiring_and_public_compatibility_tests() -> None:
    violations: list[str] = []
    for root in (ROOT / "src", ROOT / "scripts", ROOT / "tests"):
        for path in root.rglob("*.py"):
            if path in FACADE_SELF_WIRING or _is_public_compatibility_test(path):
                continue
            for module in _imported_modules(path):
                if _uses_old_module(module):
                    violations.append(f"{path.relative_to(ROOT)}:{module}")
    assert not violations, "\n".join(violations)


def test_production_runtime_has_no_interpreter_or_old_registry_dependency() -> None:
    violations: list[str] = []
    for path in (SRC / "runtime").rglob("*.py"):
        for module in _imported_modules(path):
            if module.startswith("selfrionette.input_interpreters") or module.startswith(
                "selfrionette.input_sources.registry"
            ):
                violations.append(f"{path.relative_to(ROOT)}:{module}")
    assert not violations, "\n".join(violations)


def test_mapping_facades_remain_definition_free_re_exports() -> None:
    for path in MAPPING_FACADES:
        tree = _parse(path)
        definitions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assigned_names = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        assert definitions == [], path.relative_to(ROOT)
        assert assigned_names <= {"__all__"}, path.relative_to(ROOT)


def test_internal_loadcell_runner_resolves_versioned_mapping_explicitly() -> None:
    runner = SRC / "runtime" / "runners" / "loadcell_serial_dry_run.py"
    source = runner.read_text(encoding="utf-8")
    assert 'PluginSelection("loadcell_endpoint_mapping", 1)' in source
    assert "mapping_plugin=resolve_control_mapping_plugin(" in source


def test_current_operator_docs_do_not_reference_compatibility_scripts() -> None:
    violations = [
        path.relative_to(ROOT)
        for path in (ROOT / "docs" / "operations").rglob("*.md")
        if "scripts/compatibility/" in path.read_text(encoding="utf-8")
    ]
    assert not violations


def test_catalog_and_mapping_identities_remain_canonical() -> None:
    assert INPUT_SOURCE_CATALOG.ids == (
        "analog_fixture",
        "loadcell_fixture",
        "loadcell_serial",
        "noop",
        "programmed_target",
        "replay",
        "viewer",
    )
    assert tuple(
        registration.plugin.identity.canonical_id
        for registration in INPUT_SOURCE_CATALOG.registrations
    ) == (
        "programmed_target/v1",
        "replay/v1",
        "noop/v1",
        "viewer/v1",
        "loadcell_serial/v1",
        "loadcell_fixture/v1",
        "analog_fixture/v1",
    )
    assert INPUT_SOURCE_CATALOG.aliases == (
        "programmed_target",
        "replay",
        "noop",
        "viewer",
    )
    assert CONTROL_MAPPING_REGISTRY.ids == (
        "analog_fixture_mapping",
        "loadcell_endpoint_mapping",
        "replay_mapping",
        "viewer_keyboard_gamepad_mapping",
    )
    assert tuple(plugin.identity.canonical_id for plugin in CONTROL_MAPPING_PLUGINS) == (
        "analog_fixture_mapping/v1",
        "loadcell_endpoint_mapping/v1",
        "replay_mapping/v1",
        "viewer_keyboard_gamepad_mapping/v1",
    )


def test_each_production_source_has_an_explicit_versioned_mapping_selection() -> None:
    expected = {
        "analog_fixture": "analog_fixture_mapping/v1",
        "loadcell_fixture": "loadcell_endpoint_mapping/v1",
        "loadcell_serial": "loadcell_endpoint_mapping/v1",
        "noop": "replay_mapping/v1",
        "programmed_target": "replay_mapping/v1",
        "replay": "replay_mapping/v1",
        "viewer": "viewer_keyboard_gamepad_mapping/v1",
    }
    actual = {
        registration.plugin.identity.name: (
            None
            if registration.default_control_mapping_selection is None
            else (
                f"{registration.default_control_mapping_selection.plugin_id}/"
                f"v{registration.default_control_mapping_selection.contract_version}"
            )
        )
        for registration in INPUT_SOURCE_CATALOG.registrations
    }
    assert actual == expected
