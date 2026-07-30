from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "repository" / "validate_agent_skills.py"
SPEC = importlib.util.spec_from_file_location("validate_agent_skills", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _copy_agents(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(ROOT / ".agents", target / ".agents")
    return target


def test_repository_local_skill_governance_is_valid() -> None:
    result = MODULE.validate(ROOT)

    assert result.accepted, result.errors
    assert result.skill_count == 4
    assert result.candidate_count == 4
    assert result.eval_count == 4


def test_candidate_score_total_is_deterministic(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    candidate = target / ".agents" / "skill-candidates" / "layer-aware-change-validation.toml"
    text = candidate.read_text(encoding="utf-8")
    candidate.write_text(text.replace("total = 10", "total = 9"), encoding="utf-8", newline="\n")

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("score total does not equal" in error for error in result.errors)


def test_duplicate_candidate_key_is_rejected(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    source = target / ".agents" / "skill-candidates" / "layer-aware-change-validation.toml"
    duplicate = target / ".agents" / "skill-candidates" / "another-file.toml"
    shutil.copy2(source, duplicate)

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("duplicate candidate key" in error for error in result.errors)


def test_explicit_only_policy_is_required_for_starter_skills(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    policy = target / ".agents" / "skills" / "selfrionette-pr-handoff" / "agents" / "openai.yaml"
    text = policy.read_text(encoding="utf-8")
    policy.write_text(
        text.replace("allow_implicit_invocation: false", "allow_implicit_invocation: true"),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("cannot allow implicit invocation" in error for error in result.errors)


def test_transient_branch_reference_is_rejected_from_skill_body(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    skill = target / ".agents" / "skills" / "skill-lifecycle-review" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\nDo not fix codex/example-branch in the Skill body.\n",
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("transient Issue / branch" in error for error in result.errors)


def test_transient_full_sha_is_rejected_from_skill_body(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    skill = target / ".agents" / "skills" / "skill-lifecycle-review" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\nA transient value is 05d8321e0918baec69caede2c22db398055057a6.\n",
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("transient Issue / branch / SHA" in error for error in result.errors)


def test_transient_contextual_abbreviated_sha_is_rejected_from_skill_body(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    skill = target / ".agents" / "skills" / "skill-lifecycle-review" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\nDo not pin head: 05d8321 or base SHA = 329ec5df1886.\n",
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("transient Issue / branch / SHA" in error for error in result.errors)


def test_non_sha_hex_like_text_is_not_rejected_from_skill_body(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    skill = target / ".agents" / "skills" / "skill-lifecycle-review" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\nA generic identifier is abcdef1234567.\n",
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert result.accepted, result.errors


def test_candidate_evidence_can_contain_full_sha(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    candidate = target / ".agents" / "skill-candidates" / "protected-long-form-body-safety.toml"
    text = candidate.read_text(encoding="utf-8")
    candidate.write_text(
        text.replace(
            'observable_evidence = [',
            'observable_evidence = [\n  "commit 05d8321e0918baec69caede2c22db398055057a6 was inspected.",',
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert result.accepted, result.errors


def test_candidate_create_draft_with_related_skill_is_rejected(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    candidate = target / ".agents" / "skill-candidates" / "protected-long-form-body-safety.toml"
    text = candidate.read_text(encoding="utf-8")
    candidate.write_text(
        text.replace('related_overlapping_skills = []', 'related_overlapping_skills = ["selfrionette-change-validation"]')
        .replace('proposed_action = "record"', 'proposed_action = "create-draft"'),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("cannot use create-draft" in error for error in result.errors)


def test_candidate_skill_reference_and_lifecycle_are_consistent(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    candidate = target / ".agents" / "skill-candidates" / "protected-long-form-body-safety.toml"
    text = candidate.read_text(encoding="utf-8")
    candidate.write_text(
        text.replace('status = "candidate"', 'status = "draft"')
        .replace('related_overlapping_skills = []', 'related_overlapping_skills = ["missing-skill"]')
        .replace('proposed_action = "record"', 'proposed_action = "update"'),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("unknown Skill" in error for error in result.errors)


def test_draft_candidate_without_related_skill_is_rejected(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    candidate = target / ".agents" / "skill-candidates" / "protected-long-form-body-safety.toml"
    text = candidate.read_text(encoding="utf-8")
    candidate.write_text(
        text.replace('status = "candidate"', 'status = "draft"')
        .replace('proposed_action = "record"', 'proposed_action = "update"'),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("must reference an existing Skill" in error for error in result.errors)


def test_record_only_candidate_without_related_skill_is_allowed() -> None:
    candidate = ROOT / ".agents" / "skill-candidates" / "protected-long-form-body-safety.toml"
    text = candidate.read_text(encoding="utf-8")

    assert 'status = "candidate"' in text
    assert 'proposed_action = "record"' in text
    assert 'related_overlapping_skills = []' in text
    assert MODULE.validate(ROOT).accepted


def test_candidate_provenance_can_contain_issue_and_sha_evidence() -> None:
    candidate = (
        ROOT / ".agents" / "skill-candidates" / "layer-aware-change-validation.toml"
    ).read_text(encoding="utf-8")

    assert "PR #403" in candidate
    assert "3ce7f30" in candidate
    assert MODULE.validate(ROOT).accepted
