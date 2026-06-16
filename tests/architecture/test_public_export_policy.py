from __future__ import annotations

import importlib
from pathlib import Path


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


def test_package_root_all_excludes_stub_exports() -> None:
    for module_name in PACKAGE_ROOTS:
        module = importlib.import_module(module_name)
        exported = tuple(getattr(module, "__all__", ()))
        forbidden = [name for name in exported if name.startswith(FORBIDDEN_PREFIXES)]
        assert not forbidden, f"{module_name} exports stub names from package root: {forbidden}"


def test_stub_modules_export_only_stub_classes_in_all() -> None:
    for module_name, expected_exports in STUB_EXPORTS.items():
        module = importlib.import_module(module_name)
        assert tuple(module.__all__) == expected_exports


def test_r6_i_p2_docs_record_option_a_policy() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "Option A" in text
    assert "contract-reexport" in text
