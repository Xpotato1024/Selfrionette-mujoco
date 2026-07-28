"""AST and registry guards for the Input Source Plugin P5 boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from selfrionette.plugins.input_sources.catalog import INPUT_SOURCE_CATALOG
from selfrionette.plugins.input_sources.registration import (
    INPUT_SOURCE_REGISTRATIONS,
)
from selfrionette.plugins.mappings.catalog import CONTROL_MAPPING_PLUGINS
from selfrionette.runtime.experiment.contracts import PluginAxis


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "selfrionette"
PRODUCTION_SOURCE_IDS = set(INPUT_SOURCE_CATALOG.ids)
SOURCE_PACKAGE_ROOT = SRC / "plugins" / "input_sources"
TEST_SOURCE_PACKAGE_ROOT = ROOT / "tests" / "plugins" / "input_sources"
MAPPING_TEST_ROOT = ROOT / "tests" / "plugins" / "mappings"
MAPPING_COMPATIBILITY_FACADES = {
    "keyboard.py",
    "continuous_endpoint_velocity.py",
    "analog_fixture.py",
    "loadcell_serial.py",
    "replay.py",
}
MOVED_CONCRETE_OLD_MODULES = {
    "selfrionette.input_sources.analog_fixture",
    "selfrionette.input_sources.loadcell_serial",
    "selfrionette.input_sources.programmed_target",
    "selfrionette.input_sources.replay",
    "selfrionette.input_sources.viewer",
}
MOVED_IMPLEMENTATION_SYMBOLS = {
    "AnalogFixtureSample",
    "DEFAULT_SWEEP_X_DT_S",
    "DEFAULT_SWEEP_X_FINAL_HOLD_FRAMES",
    "DEFAULT_SWEEP_X_INITIAL_HOLD_FRAMES",
    "DEFAULT_SWEEP_X_INITIAL_POSITION_M",
    "DEFAULT_SWEEP_X_MOVE_FRAMES",
    "DEFAULT_SWEEP_X_POSITIVE_X_OFFSET_M",
    "DEFAULT_SWEEP_X_RETURN_FRAMES",
    "DEFAULT_SWEEP_X_SLOW_OR_HOLD_FRAMES",
    "DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS",
    "DEFAULT_VIEWER_SAFE_ENDPOINT_M",
    "InputSource",
    "LoadcellNormalizationConfig",
    "LoadcellNormalizedInputIntentConverter",
    "NormalizedLoadcellInputIntent",
    "ProgrammedTargetFrame",
    "ProgrammedTargetInputSource",
    "ProgrammedTargetTrajectory",
    "RawLoadcellVectorRecord",
    "ReplayInputSource",
    "SerialDiagnosticEvent",
    "SerialFrameParseError",
    "SerialInputSource",
    "ViewerInputSource",
    "build_sweep_x_input_source",
    "build_sweep_x_trajectory",
    "normalize_loadcell_frame_for_mapping",
    "parse_analog_fixture_sample",
    "parse_serial_frame_line",
}


def _modules(tree: ast.AST) -> tuple[str, ...]:
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            values.append(node.module)
    return tuple(values)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _defined_top_level_symbols(path: Path) -> set[str]:
    symbols: set[str] = set()
    for node in _parse(path).body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Assign):
            symbols.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            symbols.add(node.target.id)
    return symbols


def test_input_source_is_the_sixth_composition_axis_and_catalog_is_singleton() -> None:
    assert PluginAxis.INPUT_SOURCE.value == "input_source"
    assert set(INPUT_SOURCE_CATALOG.ids) == {
        "programmed_target",
        "replay",
        "noop",
        "viewer",
        "loadcell_serial",
        "loadcell_fixture",
        "analog_fixture",
    }
    assert tuple(sorted(registration.plugin.identity.name for registration in INPUT_SOURCE_REGISTRATIONS)) == INPUT_SOURCE_CATALOG.ids
    assert len(INPUT_SOURCE_CATALOG.ids) == len(set(INPUT_SOURCE_CATALOG.ids))
    aliases = tuple(alias for registration in INPUT_SOURCE_REGISTRATIONS for alias in registration.cli_aliases)
    assert len(aliases) == len(set(aliases))
    assert all(registration.execution_adapter is not None for registration in INPUT_SOURCE_REGISTRATIONS)
    assert all(registration.plugin.produced_sample_schema for registration in INPUT_SOURCE_REGISTRATIONS)
    assert all(
        mapping.accepted_input_sample_schemas
        for mapping in CONTROL_MAPPING_PLUGINS
    )
    assert {
        mapping.identity.name for mapping in CONTROL_MAPPING_PLUGINS
    } == {
        "analog_fixture_mapping",
        "loadcell_endpoint_mapping",
        "replay_mapping",
        "viewer_keyboard_gamepad_mapping",
    }


def test_production_loadcell_source_declares_explicit_mapping_input_adapter() -> None:
    loadcell_mapping = next(
        mapping
        for mapping in CONTROL_MAPPING_PLUGINS
        if mapping.identity.name == "loadcell_endpoint_mapping"
    )
    assert "loadcell_normalized_input_intent" in {
        schema.name for schema in loadcell_mapping.accepted_input_sample_schemas
    }
    for source_id in ("loadcell_serial", "loadcell_fixture"):
        source = INPUT_SOURCE_CATALOG.resolve(source_id).plugin
        assert source.mapping_input_adapter is not None, source_id
        assert source.mapping_input_adapter.input_schema == source.produced_sample_schema
        assert source.mapping_input_adapter.output_schema in loadcell_mapping.accepted_input_sample_schemas


def test_mapping_tests_use_canonical_mapping_owners() -> None:
    violations: list[str] = []
    for path in MAPPING_TEST_ROOT.rglob("*.py"):
        tree = _parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if node.module.startswith("selfrionette.input_sources"):
                imported = {alias.name for alias in node.names}
                violations.append(f"{path}:{node.lineno}:{node.module}:{sorted(imported)}")
    for relative, module in (
        ("analog_fixture", "selfrionette.plugins.mappings.analog_fixture"),
        ("loadcell", "selfrionette.plugins.mappings.loadcell"),
        ("viewer", "selfrionette.plugins.mappings.keyboard"),
    ):
        owner_tests = tuple((MAPPING_TEST_ROOT / relative).rglob("test_*.py"))
        assert owner_tests, relative
        assert any(module in _modules(_parse(path)) for path in owner_tests), module
    assert not violations


def test_input_source_to_mapping_reverse_dependency_is_allowlisted_to_facades() -> None:
    violations: list[str] = []
    facade_paths = {
        SRC / "input_sources" / name for name in MAPPING_COMPATIBILITY_FACADES
    }
    for path in (SRC / "input_sources").rglob("*.py"):
        for module in _modules(_parse(path)):
            if module.startswith("selfrionette.plugins.mappings") and path not in facade_paths:
                violations.append(f"{path}:{module}")
    assert not violations
    expected_facade_imports = {
        "analog_fixture.py": "selfrionette.plugins.mappings.analog_fixture",
        "continuous_endpoint_velocity.py": "selfrionette.plugins.mappings.continuous_endpoint_velocity",
        "keyboard.py": "selfrionette.plugins.mappings.keyboard",
        "loadcell_serial.py": "selfrionette.plugins.mappings.loadcell",
        "replay.py": "selfrionette.plugins.mappings.replay",
    }
    for filename, canonical_module in expected_facade_imports.items():
        assert canonical_module in (SRC / "input_sources" / filename).read_text(encoding="utf-8")


def test_each_production_source_has_a_plugin_local_test_owner() -> None:
    for source_id in sorted(PRODUCTION_SOURCE_IDS):
        owner = TEST_SOURCE_PACKAGE_ROOT / source_id
        assert owner.is_dir(), source_id
        assert tuple(owner.glob("test_*.py")), source_id
    contract_owner = TEST_SOURCE_PACKAGE_ROOT / "contract"
    assert (contract_owner / "conformance.py").is_file()
    assert tuple(contract_owner.glob("test_*.py"))


def test_generic_conformance_helper_does_not_depend_on_production_private_sources() -> None:
    conformance_path = TEST_SOURCE_PACKAGE_ROOT / "contract" / "conformance.py"
    conformance_text = conformance_path.read_text(encoding="utf-8")
    assert "selfrionette.input_sources" not in conformance_text
    assert "selfrionette.plugins.input_sources" not in conformance_text


def test_runtime_has_no_source_name_dispatch() -> None:
    def source_name_expr(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Name)
            and node.id == "source_name"
        ) or (
            isinstance(node, ast.Attribute)
            and node.attr == "source_name"
        )

    def contains_known_source_literal(node: ast.AST) -> bool:
        return any(
            isinstance(item, ast.Constant)
            and isinstance(item.value, str)
            and item.value in PRODUCTION_SOURCE_IDS
            for item in ast.walk(node)
        )

    violations: list[str] = []
    for path in (SRC / "runtime").rglob("*.py"):
        tree = _parse(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and (
                source_name_expr(node.left)
                or any(source_name_expr(item) for item in node.comparators)
            ) and contains_known_source_literal(node):
                violations.append(f"{path}:{node.lineno}")
            if isinstance(node, ast.Match) and source_name_expr(node.subject):
                for case in node.cases:
                    if contains_known_source_literal(case.pattern):
                        violations.append(f"{path}:{node.lineno}")
    assert not violations


def test_source_plugin_import_graph_has_no_forbidden_or_private_cross_source_edges() -> None:
    violations: list[str] = []
    for source_id in sorted(PRODUCTION_SOURCE_IDS):
        package = SOURCE_PACKAGE_ROOT / source_id
        for path in package.rglob("*.py"):
            modules = _modules(_parse(path))
            for module in modules:
                if module.startswith("selfrionette.plugins.robots") or module.startswith(
                    "selfrionette.runtime.evaluation"
                ) or ".fast_arm" in module or ".tasks" in module:
                    violations.append(f"source:{path}:{module}")
                if module.startswith("selfrionette.plugins.input_sources."):
                    other = module.split(".")[3]
                    if other not in {"_common", "_loadcell", source_id}:
                        violations.append(f"cross-source:{path}:{module}")
    assert not violations


def test_canonical_source_code_has_no_robot_evaluation_or_mapping_dependency() -> None:
    violations: list[str] = []
    canonical_roots = (
        SOURCE_PACKAGE_ROOT / "_loadcell",
        SOURCE_PACKAGE_ROOT / "analog_fixture",
        SOURCE_PACKAGE_ROOT / "programmed_target",
        SOURCE_PACKAGE_ROOT / "replay",
        SOURCE_PACKAGE_ROOT / "viewer",
    )
    for root in canonical_roots:
        for path in root.rglob("*.py"):
            for module in _modules(_parse(path)):
                if (
                    module.startswith("selfrionette.plugins.mappings")
                    or module.startswith("selfrionette.plugins.robots")
                    or module.startswith("selfrionette.runtime.evaluation")
                    or ".fast_arm" in module
                    or ".tasks" in module
                ):
                    violations.append(f"{path}:{module}")
    assert not violations


def test_plugin_packages_do_not_import_moved_concrete_old_source_modules() -> None:
    violations: list[str] = []
    for path in SOURCE_PACKAGE_ROOT.rglob("*.py"):
        for module in _modules(_parse(path)):
            if module in MOVED_CONCRETE_OLD_MODULES:
                violations.append(f"{path}:{module}")
    assert not violations


def test_loadcell_plugins_share_deliberate_owner_without_private_cross_imports() -> None:
    for source_id in ("loadcell_fixture", "loadcell_serial"):
        modules = {
            module
            for path in (SOURCE_PACKAGE_ROOT / source_id).rglob("*.py")
            for module in _modules(_parse(path))
        }
        assert "selfrionette.plugins.input_sources._loadcell" in modules
        assert not any(
            module.startswith(
                f"selfrionette.plugins.input_sources.{'loadcell_serial' if source_id == 'loadcell_fixture' else 'loadcell_fixture'}"
            )
            for module in modules
        )


def test_old_source_modules_are_implementation_free_compatibility_facades() -> None:
    facade_paths = (
        SRC / "input_sources" / "analog_fixture.py",
        SRC / "input_sources" / "base.py",
        SRC / "input_sources" / "programmed_target.py",
        SRC / "input_sources" / "replay.py",
        SRC / "input_sources" / "viewer.py",
        SRC / "input_sources" / "loadcell_serial.py",
    )
    for path in facade_paths:
        duplicate_symbols = (
            _defined_top_level_symbols(path) & MOVED_IMPLEMENTATION_SYMBOLS
        )
        assert not duplicate_symbols, f"{path}:{sorted(duplicate_symbols)}"


def test_viewer_defaults_have_one_definition_and_no_keyboard_gamepad_source_plugins() -> None:
    definitions = {
        name: []
        for name in (
            "DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS",
            "DEFAULT_VIEWER_SAFE_ENDPOINT_M",
        )
    }
    for path in SRC.rglob("*.py"):
        symbols = _defined_top_level_symbols(path)
        for name in definitions:
            if name in symbols:
                definitions[name].append(path)
    expected = SOURCE_PACKAGE_ROOT / "viewer" / "source.py"
    assert definitions == {
        "DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS": [expected],
        "DEFAULT_VIEWER_SAFE_ENDPOINT_M": [expected],
    }
    assert not (SOURCE_PACKAGE_ROOT / "keyboard").exists()
    assert not (SOURCE_PACKAGE_ROOT / "gamepad").exists()


def test_programmed_target_defaults_have_one_canonical_definition() -> None:
    default_names = {
        "DEFAULT_SWEEP_X_INITIAL_POSITION_M",
        "DEFAULT_SWEEP_X_POSITIVE_X_OFFSET_M",
        "DEFAULT_SWEEP_X_DT_S",
        "DEFAULT_SWEEP_X_INITIAL_HOLD_FRAMES",
        "DEFAULT_SWEEP_X_MOVE_FRAMES",
        "DEFAULT_SWEEP_X_SLOW_OR_HOLD_FRAMES",
        "DEFAULT_SWEEP_X_RETURN_FRAMES",
        "DEFAULT_SWEEP_X_FINAL_HOLD_FRAMES",
    }
    definitions = {name: [] for name in default_names}
    for path in SRC.rglob("*.py"):
        symbols = _defined_top_level_symbols(path)
        for name in default_names:
            if name in symbols:
                definitions[name].append(path)

    expected = SOURCE_PACKAGE_ROOT / "programmed_target" / "source.py"
    assert definitions == {name: [expected] for name in default_names}


def test_runtime_contract_does_not_import_old_input_source_definition() -> None:
    contract_path = SRC / "runtime" / "experiment" / "input_source.py"
    assert "InputSource" in _defined_top_level_symbols(contract_path)
    assert "selfrionette.input_sources.base" not in _modules(_parse(contract_path))


def test_mapping_plugin_import_graph_does_not_acquire_devices_or_browser() -> None:
    forbidden_fragments = (
        "serial",
        "pyserial",
        "browser",
        "websocket",
        "selfrionette.input_sources.loadcell_serial",
        "selfrionette.input_sources.viewer",
    )
    violations: list[str] = []
    mapping_root = SRC / "plugins" / "mappings"
    for path in mapping_root.rglob("*.py"):
        for module in _modules(_parse(path)):
            if any(fragment in module.lower() for fragment in forbidden_fragments):
                violations.append(f"{path}:{module}")
    assert not violations


def test_legacy_registry_is_retained_only_as_a_low_level_compatibility_boundary() -> None:
    registry_path = SRC / "input_sources" / "registry.py"
    registry_text = registry_path.read_text(encoding="utf-8")
    assert "plugins.input_sources.catalog" in registry_text or "production runtime selection source of truth" in registry_text
    assert "INPUT_SOURCE_CATALOG" not in registry_text
    for root in (SRC / "runtime", SRC / "plugins"):
        for path in root.rglob("*.py"):
            assert "selfrionette.input_sources.registry" not in path.read_text(encoding="utf-8"), path


def test_retired_execution_fallback_has_no_duplicate_implementation() -> None:
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (SRC / "runtime").rglob("*.py")
    )
    assert "compatibility_execution_adapter" not in source_text


def test_legacy_direct_runner_default_path_is_bounded_and_golden_compatible() -> None:
    for relative in (
        "scripts/compatibility/run_replay_mujoco_dry_run.py",
        "scripts/compatibility/run_replay_mujoco_websocket_publisher.py",
    ):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        assert "if args.input_source is None:" in text
        assert any(
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Attribute)
            and node.left.attr == "input_source"
            and any(isinstance(item, ast.Constant) and item.value is None for item in node.comparators)
            for node in ast.walk(tree)
        )
        assert "run_replay_mujoco_" in text


def test_test_only_dummy_is_not_visible_to_production_source_code_or_cli() -> None:
    assert "test_dummy_input_source" not in INPUT_SOURCE_CATALOG.ids
    assert "test_dummy_input" not in INPUT_SOURCE_CATALOG.aliases
    production_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SRC.rglob("*.py")
    )
    assert "test_dummy_input_source" not in production_text
    assert "test_dummy_sample" not in production_text
