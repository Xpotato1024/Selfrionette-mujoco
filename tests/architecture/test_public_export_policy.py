from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOTS = (
    "selfrionette.input_sources",
    "selfrionette.input_interpreters",
    "selfrionette.kinematics",
    "selfrionette.motion",
    "selfrionette.mujoco_backend",
    "selfrionette.transport",
    "selfrionette.runtime",
)

FORBIDDEN_PREFIXES = ("NoOp", "Zero", "Static")

STUB_EXPORTS = {
    "selfrionette.input_sources.stubs": ("StaticInputSource",),
    "selfrionette.input_interpreters.stubs": ("NoOpInputInterpreter",),
    "selfrionette.kinematics.stubs": ("ZeroForwardKinematicsSolver", "ZeroInverseKinematicsSolver"),
    "selfrionette.motion.stubs": ("NoOpMotionGenerator",),
    "selfrionette.mujoco_backend.stubs": ("NoOpMuJoCoSimulator",),
    "selfrionette.transport.stubs": ("NoOpStatePublisher",),
}

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "operations" / "r6-i-p2-public-export-policy.md"
DOCS_README_PATH = ROOT / "docs" / "README.md"
R6_I_P3_DOC_PATH = ROOT / "docs" / "operations" / "r6-i-p3-stub-reclassification.md"


def test_package_root_all_excludes_stub_exports() -> None:
    for module_name in PACKAGE_ROOTS:
        module = importlib.import_module(module_name)
        exported = tuple(getattr(module, "__all__", ()))
        forbidden = [name for name in exported if name.startswith(FORBIDDEN_PREFIXES)]
        assert not forbidden, f"{module_name} exports stub names from package root: {forbidden}"


def test_input_sources_package_root_exports_programmed_target_input_source() -> None:
    module = importlib.import_module("selfrionette.input_sources")
    assert "ProgrammedTargetInputSource" in module.__all__
    assert "build_sweep_x_input_source" in module.__all__
    assert "build_sweep_x_trajectory" not in module.__all__
    assert hasattr(module, "ProgrammedTargetInputSource")
    assert hasattr(module, "build_sweep_x_input_source")
    assert not hasattr(module, "build_sweep_x_trajectory")
    assert "StaticInputSource" not in module.__all__
    assert not hasattr(module, "StaticInputSource")


def test_stub_modules_export_only_stub_classes_in_all() -> None:
    for module_name, expected_exports in STUB_EXPORTS.items():
        module = importlib.import_module(module_name)
        assert tuple(module.__all__) == expected_exports


def test_r6_i_p2_docs_record_option_a_policy() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "Option A" in text
    assert "contract-reexport" in text


def test_docs_readme_lists_r6_i_p3_stub_reclassification() -> None:
    text = DOCS_README_PATH.read_text(encoding="utf-8")
    assert "R6-I-P3 remaining stubs reclassification" in text
    assert R6_I_P3_DOC_PATH.relative_to(ROOT).as_posix() in text
