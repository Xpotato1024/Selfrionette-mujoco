from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_STATUS = {"canonical", "supporting", "historical", "draft", "obsolete"}
CANONICAL_DOCS = [
    "docs/README.md",
    "docs/conventions.md",
    "docs/architecture/development-policy.md",
    "docs/architecture/mujoco-skeleton-first-spec.md",
    "docs/architecture/documentation-sot-policy.md",
    "docs/architecture/dependency-boundaries.md",
    "docs/architecture/data-flow.md",
    "docs/architecture/runtime-composition.md",
    "docs/contracts/parallel-work-contracts.md",
    "docs/contracts/kinematics-command-contract.md",
    "docs/contracts/motion-command.md",
    "docs/contracts/schemas.md",
    "docs/contracts/mujoco-state.md",
    "docs/contracts/transport-payload.md",
    "docs/contracts/robot-profile-runtime-viewer-profile.md",
    "docs/contracts/experiment-plugin-composition.md",
    "docs/contracts/evaluation-manifest-readiness.md",
    "docs/contracts/assets.md",
    "docs/contracts/r7-b-runtime-input-pipeline-contract.md",
    "docs/operations/git-pr-workflow.md",
    "docs/operations/validation.md",
    "docs/operations/hardware-safety.md",
    "docs/operations/codex-workflow.md",
    "docs/operations/r7-c-viewer-fixture-demo-procedure.md",
    "docs/operations/r7-c-keyboard-replay-demo-package.md",
    "docs/operations/r7-c-live-selfrionette-validation-log.md",
    "docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md",
    "docs/operations/r7-c-axis-sanity-check.md",
    "docs/experiment-notes/templates/r7-c-axis-sanity-check-template.md",
    "docs/reports/implementation/r7-c-presentation-demo-notes.md",
    "docs/reports/audits/r7-c-completion-audit.md",
    "docs/operations/r7-e-p1-fast-arm-endpoint-motion-sanity.md",
    "docs/reports/implementation/r7-e-p22-neutral-initial-pose.md",
    "docs/migration/legacy-inventory.md",
    "docs/migration/legacy-to-new-layer-map.md",
    "docs/migration/rapier-to-mujoco-migration.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def front_matter(text: str) -> str:
    assert text.startswith("---\n"), "missing opening front matter delimiter"
    end = text.find("\n---\n", 4)
    assert end != -1, "missing closing front matter delimiter"
    return text[4:end]


def status_value(front: str) -> str:
    for line in front.splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("front matter missing status")


def test_docs_sot_required_paths_exist() -> None:
    required = [
        "docs/README.md",
        "docs/conventions.md",
        "docs/architecture/documentation-sot-policy.md",
        "docs/architecture/dependency-boundaries.md",
    ]

    for path in required:
        assert (ROOT / path).is_file(), path


def test_doc_directory_is_not_used() -> None:
    assert not (ROOT / "doc").exists()


def test_canonical_docs_have_valid_front_matter() -> None:
    for path in CANONICAL_DOCS:
        front = front_matter(read(path))
        assert status_value(front) in ALLOWED_STATUS, path


def test_docs_readme_has_source_of_truth_map() -> None:
    text = read("docs/README.md")
    assert "Source of Truth Map" in text


def test_current_contracts_are_registered_and_evidence_is_not_in_sot_map() -> None:
    index = read("docs/README.md")
    operations = read("docs/operations/README.md")
    reports = read("docs/reports/README.md")
    archive = read("docs/archive/README.md")

    assert "`docs/contracts/analog-fixture-mapping.md`" in index
    assert "| Topic | Canonical document | Notes |" in index
    assert "docs/contracts/kinematics-command-contract.md" in index
    assert "`research/README.md`" in index
    assert "r7-c-manual-validation-preflight.md" not in operations
    assert "r7-c-manual-validation-preflight.md" in reports
    assert "native-mujoco-fast-arm-viewer-check.md" not in operations
    assert "native-mujoco-fast-arm-viewer-check.md" in archive
    assert "r7-c-viewer-fixture-demo-procedure.md" in operations
    assert "r7-c-keyboard-replay-demo-package.md" in operations
    assert "r7-c-live-selfrionette-validation-log.md" in operations
    assert "r7-c-axis-sanity-check.md" in operations
    assert "docs/reports/implementation/r7-c-presentation-demo-notes.md" not in index
    assert "docs/reports/audits/r7-c-completion-audit.md" not in index
    assert (ROOT / "docs/reports/implementation/r7-c-manual-validation-preflight.md").is_file()
    assert (ROOT / "docs/archive/operations/native-mujoco-fast-arm-viewer-check.md").is_file()


def test_runtime_composition_documents_current_responsibility_split() -> None:
    text = read("docs/architecture/runtime-composition.md")
    stages = (
        "source planning",
        "source lifecycle",
        "control-frame resolution",
        "motion policy",
        "backend update",
        "MuJoCo measurement",
        "diagnostic annotation",
        "publication",
        "target lifecycle",
        "experiment record construction",
    )

    for stage in stages:
        assert f"| {stage} |" in text

    assert "MuJoCo remains the physical source of truth" in text
    assert "only composition root" in text
    assert "render-only" in text
    assert "publish-before-ViewerInputSource-rebase" in text
    assert "does not perform a broad runtime rewrite" in text


def test_robot_profile_contract_is_canonical_and_registered() -> None:
    index = read("docs/README.md")
    text = read("docs/contracts/robot-profile-runtime-viewer-profile.md")

    assert "`docs/contracts/robot-profile-runtime-viewer-profile.md`" in index
    assert "RobotRuntimePlugin" in text
    assert "ViewerRobotProfile" in text
    assert "arbitrary dynamic" in text
    assert "payload-v0" in text
    assert "rendering declaration" in text
    assert "ProviderAssemblyBinding" in text
    assert "RuntimeConfig.robot_selection" in text
    assert "symlink解決後の実path" in text


def test_experiment_plugin_composition_contract_is_canonical_and_registered() -> None:
    index = read("docs/README.md")
    text = read("docs/contracts/experiment-plugin-composition.md")

    assert "`docs/contracts/experiment-plugin-composition.md`" in index
    for marker in (
        "Robot Bundle",
        "Environment / Scene",
        "Control / Mapping",
        "Task",
        "Evaluation",
        "Input Source",
        "contact_evidence/v1",
        "PluginParameterOwner",
        "EvidenceProducerBinding",
        "SemanticRoleRequirement",
        "exact `VersionedIdentity`",
        "ambiguous producer",
        "requested",
        "resolved",
        "predicted",
        "measured",
        "unavailable",
        "invalid",
        "compose_experiment()",
        "#405",
        "#411",
    ):
        assert marker in text


def test_evaluation_manifest_readiness_contract_is_canonical_and_registered() -> None:
    index = read("docs/README.md")
    text = read("docs/contracts/evaluation-manifest-readiness.md")

    assert "`docs/contracts/evaluation-manifest-readiness.md`" in index
    for marker in (
        "EvaluationManifest",
        "evaluation-manifest/v2",
        "canonical JSON",
        "sha256",
        "FreezeRecord",
        "requested identity",
        "resolved identity",
        "world / tool condition-pair",
        "condition_specific",
        "software-only",
        "#423",
        "#406",
        "partial success",
    ):
        assert marker in text


def test_p22_neutral_pose_contract_is_registered_and_freezes_selection_order() -> None:
    index = read("docs/README.md")
    evidence = read("docs/reports/implementation/r7-e-p22-neutral-initial-pose.md")
    contract = read("docs/contracts/robot-profile-runtime-viewer-profile.md")

    assert "`docs/contracts/robot-profile-runtime-viewer-profile.md`" in index
    assert "`docs/reports/implementation/r7-e-p22-neutral-initial-pose.md`" not in index
    assert "(0, -0.5235987755982989, 0, -1.0471975511965976)" in contract
    assert "tip = (0.240000, -0.245951, 0.284308) m" in contract
    assert "collision-freeの物理証拠とは扱わない" in contract
    assert "Selection contract fixed before evaluation" in evidence
    assert "rank 3は必須にしない" in evidence
    assert "MuJoCo native `home` keyframe" in evidence
    assert "candidate count: `82`" in evidence
    assert "#339 / P6: implementation evidence complete; manual viewer smoke required" in evidence
    assert (
        "#341 / P7: local-policy evidence complete with documented workspace limitation; "
        "manual viewer smoke required"
    ) in evidence
    assert "collision_check_available=false" in evidence
