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


def test_candidate_provenance_can_contain_issue_and_sha_evidence() -> None:
    candidate = (
        ROOT / ".agents" / "skill-candidates" / "layer-aware-change-validation.toml"
    ).read_text(encoding="utf-8")

    assert "PR #403" in candidate
    assert "3ce7f30" in candidate
    assert MODULE.validate(ROOT).accepted
