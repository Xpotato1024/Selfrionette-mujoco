from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tomllib


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


def test_explicit_only_eval_rejects_implicit_policy(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    eval_path = target / ".agents" / "skill-evals" / "selfrionette-pr-handoff.toml"
    text = eval_path.read_text(encoding="utf-8")
    eval_path.write_text(
        text.replace('invocation_policy = "implicit-after-validation"', 'invocation_policy = "explicit-only"'),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("cannot allow implicit invocation" in error for error in result.errors)


def test_validated_active_implicit_skills_are_accepted() -> None:
    result = MODULE.validate(ROOT)

    assert result.accepted, result.errors
    for skill_name in MODULE.EXPECTED_IMPLICIT_SKILLS:
        eval_path = ROOT / ".agents" / "skill-evals" / f"{skill_name}.toml"
        eval_data = tomllib.loads(eval_path.read_text(encoding="utf-8"))
        policy = ROOT / ".agents" / "skills" / skill_name / "agents" / "openai.yaml"
        assert eval_data["invocation_policy"] == "implicit-after-validation"
        assert eval_data["validation_status"] == "validated"
        assert "allow_implicit_invocation: true" in policy.read_text(encoding="utf-8")


def test_draft_skill_cannot_allow_implicit_invocation(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    eval_path = target / ".agents" / "skill-evals" / "selfrionette-pr-handoff.toml"
    eval_path.write_text(
        eval_path.read_text(encoding="utf-8").replace(
            'validation_status = "validated"', 'validation_status = "draft"'
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("draft Skill cannot allow implicit invocation" in error for error in result.errors)


def test_incomplete_validation_cannot_allow_implicit_invocation(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    eval_path = target / ".agents" / "skill-evals" / "selfrionette-pr-handoff.toml"
    eval_path.write_text(
        eval_path.read_text(encoding="utf-8").replace(
            'validation_status = "validated"', 'validation_status = "pending"'
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("invalid eval validation_status" in error for error in result.errors)
    assert any("cannot allow implicit invocation" in error for error in result.errors)


def test_unresolved_approval_cannot_allow_implicit_invocation(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    eval_path = target / ".agents" / "skill-evals" / "selfrionette-plugin-change.toml"
    eval_path.write_text(
        eval_path.read_text(encoding="utf-8").replace(
            "unresolved_approval = false", "unresolved_approval = true"
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("unresolved approval" in error for error in result.errors)


def test_side_effectful_policy_cannot_allow_implicit_invocation(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    eval_path = target / ".agents" / "skill-evals" / "selfrionette-plugin-change.toml"
    eval_path.write_text(
        eval_path.read_text(encoding="utf-8").replace(
            'side_effect_policy = "instruction-only"', 'side_effect_policy = "side-effectful"'
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("side-effectful Skill" in error for error in result.errors)


def test_implicit_invocation_cannot_grant_permissions(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    config = target / ".agents" / "skill-system.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "implicit_invocation_grants_permissions = false",
            "implicit_invocation_grants_permissions = true",
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("must not grant permissions" in error for error in result.errors)


def test_policy_value_outside_policy_section_or_in_comment_is_not_adopted(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    policy = target / ".agents" / "skills" / "selfrionette-pr-handoff" / "agents" / "openai.yaml"
    policy.write_text(
        policy.read_text(encoding="utf-8").replace(
            "\npolicy:\n",
            "\n  allow_implicit_invocation: false\n"
            "# allow_implicit_invocation: false\n"
            "policy:\n",
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert result.accepted, result.errors


def test_unconditional_skill_chaining_fixture_is_rejected(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    eval_path = target / ".agents" / "skill-evals" / "selfrionette-plugin-change.toml"
    eval_path.write_text(
        eval_path.read_text(encoding="utf-8").replace(
            "automatic_chain = false", "automatic_chain = true"
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("must not require unconditional Skill chaining" in error for error in result.errors)


def test_routing_fixtures_select_the_narrow_skill_and_preserve_boundaries() -> None:
    evals = {
        path.stem: tomllib.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / ".agents" / "skill-evals").glob("*.toml")
    }
    plugin_case = evals["selfrionette-plugin-change"]["routing_cases"][0]
    validation_case = evals["selfrionette-change-validation"]["routing_cases"][0]
    handoff_case = evals["selfrionette-pr-handoff"]["routing_cases"][0]

    assert plugin_case["primary_skill"] == "selfrionette-plugin-change"
    assert validation_case["primary_skill"] == "selfrionette-change-validation"
    assert handoff_case["primary_skill"] == "selfrionette-pr-handoff"
    assert all(
        not case["automatic_chain"] and not case["permission_grant"]
        for data in evals.values()
        for case in data["routing_cases"]
    )


def test_representative_metadata_routing_scenarios_are_bounded() -> None:
    evals = {
        path.stem: tomllib.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / ".agents" / "skill-evals").glob("*.toml")
    }
    unrelated = "このrepositoryと無関係な一般質問に答えてください。"

    assert any("docs" in prompt for prompt in evals["selfrionette-change-validation"]["positive_triggers"])
    assert any(
        "pluginと無関係" in prompt
        for prompt in evals["selfrionette-plugin-change"]["negative_triggers"]
    )
    assert any(
        "read-only" in prompt for prompt in evals["selfrionette-pr-handoff"]["positive_triggers"]
    )
    assert all(unrelated in data["negative_triggers"] for data in evals.values())
    assert "Issue / PR mutation" in evals["skill-lifecycle-review"]["forbidden_actions"]
    assert "serial / OSC / robot output" in evals["selfrionette-change-validation"]["forbidden_actions"]
    assert "external mutation" in evals["selfrionette-plugin-change"]["forbidden_actions"]
    assert "commit" in evals["selfrionette-pr-handoff"]["forbidden_actions"]


def test_active_candidate_without_implemented_skill_is_rejected(tmp_path: Path) -> None:
    target = _copy_agents(tmp_path)
    candidate = target / ".agents" / "skill-candidates" / "protected-long-form-body-safety.toml"
    candidate.write_text(
        candidate.read_text(encoding="utf-8").replace(
            'status = "candidate"', 'status = "active"'
        ),
        encoding="utf-8",
        newline="\n",
    )

    result = MODULE.validate(target)

    assert not result.accepted
    assert any("unimplemented candidate cannot be active" in error for error in result.errors)


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
