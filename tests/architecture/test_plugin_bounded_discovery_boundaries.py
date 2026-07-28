from __future__ import annotations

import ast
from pathlib import Path

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.mappings.catalog import CONTROL_MAPPING_REGISTRY


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "selfrionette"
PLUGINS = SRC / "plugins"


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.append(node.module)
    return tuple(values)


def test_discoverable_axes_use_fixed_package_entry_points() -> None:
    assert (PLUGINS / "robots" / "fast_arm" / "plugin.py").is_file()
    for plugin_id in INPUT_SOURCE_CATALOG.ids:
        entry = PLUGINS / "input_sources" / plugin_id / "plugin.py"
        assert entry.is_file(), plugin_id
        assert "INPUT_SOURCE_PLUGIN" in entry.read_text(encoding="utf-8")
    for plugin_id in CONTROL_MAPPING_REGISTRY.ids:
        entry = PLUGINS / "mappings" / plugin_id / "plugin.py"
        assert entry.is_file(), plugin_id
        assert "CONTROL_MAPPING_PLUGIN" in entry.read_text(encoding="utf-8")


def test_catalogs_and_generic_registration_do_not_list_concrete_plugins() -> None:
    guarded = (
        PLUGINS / "input_sources" / "catalog.py",
        PLUGINS / "mappings" / "catalog.py",
        PLUGINS / "input_source_registration.py",
    )
    concrete_ids = (
        *INPUT_SOURCE_CATALOG.ids,
        *CONTROL_MAPPING_REGISTRY.ids,
    )
    for path in guarded:
        text = path.read_text(encoding="utf-8")
        assert not any(plugin_id in text for plugin_id in concrete_ids), path
        assert not any(
            module.startswith("selfrionette.plugins.input_sources.")
            or module.startswith("selfrionette.plugins.mappings.")
            for module in _imports(path)
        ), path


def test_discovery_is_bounded_and_axis_validation_stays_typed() -> None:
    helper = (PLUGINS / "bounded_discovery.py").read_text(encoding="utf-8")
    assert "pkgutil.iter_modules(namespace.__path__)" in helper
    assert "item.ispkg" in helper
    assert 'item.name.startswith("_")' in helper
    assert "sorted(" in helper
    assert "importlib.import_module(module_name)" in helper
    assert "entry_points" not in helper
    assert "sys.path" not in helper

    input_discovery = (
        PLUGINS / "input_source_discovery.py"
    ).read_text(encoding="utf-8")
    mapping_discovery = (
        PLUGINS / "control_mapping_discovery.py"
    ).read_text(encoding="utf-8")
    assert 'INPUT_SOURCE_PLUGIN_ENTRY_MODULE = "plugin"' in input_discovery
    assert (
        'INPUT_SOURCE_PLUGIN_ENTRY_SYMBOL = "INPUT_SOURCE_PLUGIN"'
        in input_discovery
    )
    assert 'CONTROL_MAPPING_PLUGIN_ENTRY_MODULE = "plugin"' in mapping_discovery
    assert (
        'CONTROL_MAPPING_PLUGIN_ENTRY_SYMBOL = "CONTROL_MAPPING_PLUGIN"'
        in mapping_discovery
    )
    assert "isinstance(registration, InputSourcePluginRegistration)" in (
        input_discovery
    )
    assert "isinstance(plugin, ControlMappingPlugin)" in mapping_discovery


def test_mapping_implementation_is_package_owned_without_cross_plugin_imports() -> None:
    mapping_root = PLUGINS / "mappings"
    plugin_ids = set(CONTROL_MAPPING_REGISTRY.ids)
    for plugin_id in sorted(plugin_ids):
        package = mapping_root / plugin_id
        assert (package / "implementation.py").is_file()
        for path in package.rglob("*.py"):
            for module in _imports(path):
                for other in plugin_ids - {plugin_id}:
                    assert not module.startswith(
                        f"selfrionette.plugins.mappings.{other}"
                    ), f"{path}:{module}"

    shared = mapping_root / "_continuous_endpoint_velocity.py"
    assert shared.is_file()
    shared_text = shared.read_text(encoding="utf-8")
    assert not any(plugin_id in shared_text for plugin_id in plugin_ids)


def test_environment_task_evaluation_have_no_production_concrete_second_sot() -> None:
    for axis in ("environments", "tasks", "evaluations"):
        namespace = PLUGINS / axis
        assert namespace.is_dir()
        assert tuple(
            path.name
            for path in namespace.iterdir()
            if not path.name.startswith("_")
        ) == ()


def test_generic_experiment_layer_has_no_concrete_plugin_imports() -> None:
    violations: list[str] = []
    for path in (SRC / "runtime" / "experiment").rglob("*.py"):
        for module in _imports(path):
            if module.startswith("selfrionette.plugins.input_sources.") or (
                module.startswith("selfrionette.plugins.mappings.")
            ):
                violations.append(f"{path}:{module}")
    assert not violations
