"""Validate the repository-local Skill opt-in, registry, and starter Skills."""

from __future__ import annotations

from dataclasses import dataclass, field
import argparse
from pathlib import Path
import re
import sys
import tomllib
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(".agents/skill-system.toml")
SKILLS_PATH = Path(".agents/skills")
MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u7e3a",
    "\u7e67",
    "\u8700",
    "\u9aea",
    "\u8b17",
    "\u9036",
    "\u8b5b",
    "\u83a0",
    "\u7e32",
    "\u0080",
)
PLACEHOLDER_PATTERN = re.compile(r"\b(?:TODO|FIXME|PLACEHOLDER)\b|\[TODO", re.IGNORECASE)
SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)
TRANSIENT_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])#\d+\b"),
    re.compile(r"\b(?:codex|origin|feature|bugfix|hotfix|release)/[A-Za-z0-9._/-]+"),
    re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
    re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][^\s`]+"),
    re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home|mnt)/[^\s`]+"),
    re.compile(r"(?<![A-Za-z0-9_])~[\\/][^\s`]+"),
    re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{40}(?![0-9A-Fa-f])"),
    re.compile(
        r"(?i)\b(?:commit|sha|head|base)(?:\s+sha)?\s*(?:[:=]\s*|\s+)[0-9a-f]{7,39}\b"
    ),
)
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_FRONTMATTER_KEYS = {"name", "description"}
ALLOWED_STATUSES = {"observed", "candidate", "draft", "active", "deprecated", "rejected"}
ALLOWED_ACTIONS = {
    "none",
    "record",
    "update",
    "create-draft",
    "promote",
    "merge",
    "disable",
    "deprecate",
    "approval-required",
}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skill_count: int = 0
    candidate_count: int = 0
    eval_count: int = 0

    @property
    def accepted(self) -> bool:
        return not self.errors


def _add(result: ValidationResult, message: str) -> None:
    result.errors.append(message)


def _parse_toml(path: Path, result: ValidationResult) -> dict[str, Any] | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        _add(result, f"TOML cannot be read as UTF-8: {path}: {exc}")
    except tomllib.TOMLDecodeError as exc:
        _add(result, f"invalid TOML: {path}: {exc}")
    return None


def _read_text(path: Path, result: ValidationResult) -> str | None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        _add(result, f"file cannot be read: {path}: {exc}")
        return None
    if data.startswith(b"\xef\xbb\xbf"):
        _add(result, f"UTF-8 BOM is not allowed: {path}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _add(result, f"not UTF-8: {path}: {exc}")
        return None
    if "\r" in text and path.suffix in {".md", ".toml", ".py"}:
        _add(result, f"line endings must be LF: {path}")
    found = [marker for marker in MOJIBAKE_MARKERS if marker in text]
    if found:
        _add(result, f"mojibake-like marker in {path}: {found!r}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            _add(result, f"secret-like value in {path}")
            break
    return text


def _nonempty_strings(value: Any, field_name: str, path: Path, result: ValidationResult) -> bool:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        _add(result, f"{field_name} must be a non-empty string list: {path}")
        return False
    return True


def _nonempty_string(value: Any, field_name: str, path: Path, result: ValidationResult) -> bool:
    if not isinstance(value, str) or not value.strip():
        _add(result, f"{field_name} must be a non-empty string: {path}")
        return False
    return True


def _validate_config(root: Path, result: ValidationResult) -> dict[str, Any] | None:
    path = root / CONFIG_PATH
    if not path.is_file():
        _add(result, f"repository opt-in file is missing: {CONFIG_PATH}")
        return None
    data = _parse_toml(path, result)
    if data is None:
        return None

    required = {"schema_version", "enabled", "human_facing_language", "candidate_store", "eval_store", "thresholds", "autonomy", "invocation"}
    if set(data) != required:
        _add(result, f"skill-system.toml keys must be exactly {sorted(required)}")
    if data.get("schema_version") != 1:
        _add(result, "skill-system.toml schema_version must be 1")
    if data.get("enabled") is not True:
        _add(result, "skill-system.toml enabled must be true")
    if data.get("human_facing_language") != "ja":
        _add(result, "skill-system.toml human_facing_language must be 'ja'")

    paths: dict[str, Path] = {}
    for key in ("candidate_store", "eval_store"):
        value = data.get(key)
        if not isinstance(value, str) or not value.startswith(".agents/") or ".." in Path(value).parts:
            _add(result, f"{key} must be a repository-local .agents path")
        else:
            paths[key] = Path(value)

    thresholds = data.get("thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != {"candidate_record", "draft_creation", "promotion_review"}:
        _add(result, "thresholds must contain candidate_record, draft_creation, promotion_review")
    else:
        values = [thresholds[key] for key in ("candidate_record", "draft_creation", "promotion_review")]
        if not all(isinstance(value, int) and 0 <= value <= 10 for value in values):
            _add(result, "thresholds must be integer values from 0 through 10")
        elif not values[0] <= values[1] <= values[2]:
            _add(result, "thresholds must be ordered candidate_record <= draft_creation <= promotion_review")

    autonomy = data.get("autonomy")
    required_autonomy = {
        "instruction_only_repository_skill_auto_create_or_update",
        "executable_script_change_approval",
        "user_global_skill_change",
        "external_side_effect_skill_approval",
        "incidental_skill_change",
    }
    if not isinstance(autonomy, dict) or set(autonomy) != required_autonomy:
        _add(result, "autonomy keys do not match the repository-local minimum schema")
    else:
        if autonomy["instruction_only_repository_skill_auto_create_or_update"] is not True:
            _add(result, "instruction-only repository Skill auto create/update must be true")
        if autonomy["executable_script_change_approval"] != "explicit-approval":
            _add(result, "executable script changes must require explicit-approval")
        if autonomy["user_global_skill_change"] != "prohibited":
            _add(result, "user-global Skill changes must be prohibited")
        if autonomy["external_side_effect_skill_approval"] != "explicit-approval":
            _add(result, "external-side-effect Skills must require explicit-approval")
        if autonomy["incidental_skill_change"] != "separate-commit-or-follow-up":
            _add(result, "incidental Skill changes must be separated from product changes")

    invocation = data.get("invocation")
    required_invocation = {
        "new_skill_default",
        "validated_active_skill_default",
        "automatic_activation_after_validation",
        "implicit_invocation_requires_validation",
        "implicit_invocation_grants_permissions",
        "active_candidate_actions",
    }
    if not isinstance(invocation, dict) or set(invocation) != required_invocation:
        _add(result, "invocation keys do not match the repository-local minimum schema")
    else:
        if invocation["new_skill_default"] != "explicit-only":
            _add(result, "new Skill default invocation must be explicit-only")
        if invocation["validated_active_skill_default"] != "implicit":
            _add(result, "validated active Skill default invocation must be implicit")
        if invocation["automatic_activation_after_validation"] is not True:
            _add(result, "validated Skills must activate automatically after validation")
        if invocation["implicit_invocation_requires_validation"] is not True:
            _add(result, "implicit invocation must require validation")
        if invocation["implicit_invocation_grants_permissions"] is not False:
            _add(result, "implicit invocation must not grant permissions")
        active_actions = invocation["active_candidate_actions"]
        if (
            not isinstance(active_actions, list)
            or not active_actions
            or not all(
                isinstance(action, str) and action in ALLOWED_ACTIONS
                for action in active_actions
            )
        ):
            _add(result, "active_candidate_actions must contain allowed candidate actions")
    return {**data, "_paths": paths}


def _validate_frontmatter(text: str, path: Path, result: ValidationResult) -> tuple[str, str] | None:
    if not text.startswith("---\n"):
        _add(result, f"missing opening frontmatter delimiter: {path}")
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        _add(result, f"missing closing frontmatter delimiter: {path}")
        return None
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.fullmatch(r"([a-z_]+):\s*(.*?)\s*", line)
        if match is None:
            _add(result, f"frontmatter is outside the supported key: value subset: {path}")
            continue
        key, value = match.groups()
        if key in fields:
            _add(result, f"duplicate frontmatter key {key!r}: {path}")
        fields[key] = value.strip().strip('"')
    if set(fields) != REQUIRED_FRONTMATTER_KEYS:
        _add(result, f"frontmatter keys must be exactly name and description: {path}")
    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        _add(result, f"frontmatter name is empty: {path}")
    if not description or PLACEHOLDER_PATTERN.search(description):
        _add(result, f"frontmatter description is empty or placeholder: {path}")
    return name, description


def _policy_implicit_value(text: str, policy_path: Path, result: ValidationResult) -> bool | None:
    section = ""
    values: list[bool] = []
    for raw_line in text.splitlines():
        content = raw_line.split("#", 1)[0].rstrip()
        if not content.strip():
            continue
        if not raw_line.startswith((" ", "\t")):
            section_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):\s*", content)
            section = section_match.group(1) if section_match else ""
            continue
        if section != "policy":
            continue
        value_match = re.fullmatch(
            r"\s+allow_implicit_invocation:\s*(true|false)\s*", content
        )
        if value_match:
            values.append(value_match.group(1) == "true")
    if len(values) != 1:
        _add(
            result,
            f"Skill policy must declare exactly one policy.allow_implicit_invocation boolean: {policy_path}",
        )
        return None
    return values[0]


def _validate_skill_policy(
    skill_dir: Path, eval_data: dict[str, Any] | None, result: ValidationResult
) -> bool | None:
    policy_path = skill_dir / "agents" / "openai.yaml"
    if not policy_path.is_file():
        _add(result, f"Skill policy file is missing: {policy_path}")
        return
    text = _read_text(policy_path, result)
    if text is None:
        return None
    allow_implicit = _policy_implicit_value(text, policy_path, result)
    if allow_implicit is None:
        return None
    if eval_data is not None:
        invocation = eval_data.get("invocation_policy")
        if invocation == "explicit-only" and allow_implicit:
            _add(result, f"explicit-only Skill cannot allow implicit invocation: {skill_dir}")
        if eval_data.get("validation_status") != "validated" and allow_implicit:
            _add(result, f"unvalidated or draft Skill cannot allow implicit invocation: {skill_dir}")
        if eval_data.get("unresolved_approval") is not False and allow_implicit:
            _add(result, f"Skill with unresolved approval cannot allow implicit invocation: {skill_dir}")
        if eval_data.get("side_effect_policy") != "instruction-only" and allow_implicit:
            _add(result, f"side-effectful Skill cannot allow implicit invocation: {skill_dir}")
    return allow_implicit


def _validate_skills(root: Path, result: ValidationResult, evals: dict[str, dict[str, Any]]) -> dict[str, Path]:
    skills_root = root / SKILLS_PATH
    skill_dirs = sorted(path.parent for path in skills_root.glob("*/SKILL.md")) if skills_root.is_dir() else []
    if not skill_dirs:
        _add(result, "no repository-local Skills were found")
    names: dict[str, Path] = {}
    for skill_dir in skill_dirs:
        path = skill_dir / "SKILL.md"
        text = _read_text(path, result)
        if text is None:
            continue
        parsed = _validate_frontmatter(text, path, result)
        if parsed is None:
            continue
        name, _ = parsed
        if skill_dir.name != name:
            _add(result, f"Skill directory name and frontmatter name differ: {skill_dir.name} != {name}")
        if not SKILL_NAME_PATTERN.fullmatch(name):
            _add(result, f"Skill name must be lowercase-hyphenated: {path}")
        if name in names:
            _add(result, f"duplicate Skill name: {name}")
        names[name] = skill_dir
        body = text[text.find("\n---\n", 4) + 5 :] if "\n---\n" in text else text
        if PLACEHOLDER_PATTERN.search(body):
            _add(result, f"placeholder remains in Skill body: {path}")
        for pattern in TRANSIENT_PATTERNS:
            if pattern.search(body):
                _add(result, f"transient Issue / branch / SHA / date / local path in Skill body: {path}")
                break
        for match in re.finditer(r"(?<![A-Za-z0-9_])(?:\./)?(?:references|assets|scripts)/[A-Za-z0-9._/~+-]+", body):
            reference = match.group(0).lstrip("./")
            if not (skill_dir / reference).exists():
                _add(result, f"referenced Skill resource does not exist: {path} -> {reference}")
    result.skill_count = len(skill_dirs)
    return names


def _validate_candidates(
    root: Path,
    config: dict[str, Any],
    result: ValidationResult,
    skill_names: set[str],
) -> dict[str, dict[str, Any]]:
    store = root / config["_paths"]["candidate_store"]
    if not store.is_dir():
        _add(result, f"candidate store directory is missing: {store}")
        return {}
    paths = sorted(store.glob("*.toml"))
    if not paths:
        _add(result, "candidate store must contain at least one candidate")
    seen: dict[str, Path] = {}
    candidates: dict[str, dict[str, Any]] = {}
    required = {
        "schema_version", "candidate_key", "status", "scope", "summary", "observable_evidence",
        "realized_by_skills", "related_overlapping_skills", "approval_boundary", "unresolved_risks",
        "proposed_action", "score",
    }
    for path in paths:
        data = _parse_toml(path, result)
        if data is None:
            continue
        if not required <= set(data):
            _add(result, f"candidate schema is missing required fields: {path}")
            continue
        key = data.get("candidate_key")
        if not isinstance(key, str) or not key:
            _add(result, f"candidate_key must be a non-empty string: {path}")
            continue
        if key != path.stem:
            _add(result, f"candidate_key must match filename: {path}")
        if key in seen:
            _add(result, f"duplicate candidate key {key!r}: {seen[key]} and {path}")
        seen[key] = path
        candidates[key] = data
        if data.get("schema_version") != 1:
            _add(result, f"candidate schema_version must be 1: {path}")
        if data.get("status") not in ALLOWED_STATUSES:
            _add(result, f"invalid candidate status: {path}")
        if data.get("proposed_action") not in ALLOWED_ACTIONS:
            _add(result, f"invalid candidate action: {path}")
        for field_name in ("scope", "summary", "approval_boundary"):
            _nonempty_string(data.get(field_name), field_name, path, result)
        for field_name in (
            "observable_evidence",
            "realized_by_skills",
            "related_overlapping_skills",
            "unresolved_risks",
        ):
            value = data.get(field_name)
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                _add(result, f"{field_name} must be a string list: {path}")
        realized = data.get("realized_by_skills")
        related = data.get("related_overlapping_skills")
        if isinstance(realized, list) and all(
            isinstance(item, str) and item.strip() for item in realized
        ):
            if len(realized) != len(set(realized)):
                _add(result, f"realized_by_skills must not contain duplicates: {path}")
            for skill_name in realized:
                if skill_name not in skill_names:
                    _add(result, f"candidate realizes unknown Skill {skill_name!r}: {path}")
            if data.get("status") in {"draft", "active"} and not realized:
                _add(result, f"draft or active candidate must realize at least one Skill: {path}")
        if isinstance(related, list) and all(isinstance(item, str) and item.strip() for item in related):
            if len(related) != len(set(related)):
                _add(result, f"related_overlapping_skills must not contain duplicates: {path}")
            for skill_name in related:
                if skill_name not in skill_names:
                    _add(result, f"candidate overlaps unknown Skill {skill_name!r}: {path}")
        if (
            isinstance(realized, list)
            and isinstance(related, list)
            and all(isinstance(item, str) for item in realized + related)
        ):
            confused = set(realized) & set(related)
            if confused:
                _add(
                    result,
                    f"realized_by_skills and related_overlapping_skills must be disjoint: {path}: "
                    f"{sorted(confused)}",
                )
        score = data.get("score")
        score_keys = {"recurrence", "reconstruction_cost", "error_prevention", "stability", "verifiability", "total"}
        if not isinstance(score, dict) or set(score) != score_keys:
            _add(result, f"candidate score must contain exactly the five axes and total: {path}")
        else:
            axes = [score[key] for key in sorted(score_keys - {"total"})]
            if not all(isinstance(value, int) and 0 <= value <= 2 for value in axes):
                _add(result, f"candidate score axes must be integers from 0 through 2: {path}")
            if not isinstance(score["total"], int) or score["total"] != sum(axes):
                _add(result, f"candidate score total does not equal the axis sum: {path}")
            if isinstance(score["total"], int) and not 0 <= score["total"] <= 10:
                _add(result, f"candidate score total must be from 0 through 10: {path}")
    result.candidate_count = len(paths)
    return candidates


def _validate_evals(root: Path, config: dict[str, Any], skill_dirs: dict[str, Path], result: ValidationResult) -> dict[str, dict[str, Any]]:
    store = root / config["_paths"]["eval_store"]
    if not store.is_dir():
        _add(result, f"eval store directory is missing: {store}")
        return {}
    paths = sorted(store.glob("*.toml"))
    if {path.stem for path in paths} != set(skill_dirs):
        _add(result, "each Skill must have exactly one matching eval TOML")
    required = {
        "schema_version", "skill_name", "invocation_policy", "validation_status", "side_effect_policy",
        "unresolved_approval", "side_effect_boundary", "positive_triggers",
        "negative_triggers", "route_boundaries", "required_inputs", "expected_major_steps", "expected_outputs",
        "forbidden_actions", "representative_dry_run", "false_positive_risk", "false_negative_risk",
        "stale_reference_risk", "routing_cases",
    }
    evals: dict[str, dict[str, Any]] = {}
    for path in paths:
        data = _parse_toml(path, result)
        if data is None:
            continue
        if not required <= set(data):
            _add(result, f"eval schema is missing required fields: {path}")
            continue
        name = data.get("skill_name")
        if name != path.stem or name not in skill_dirs:
            _add(result, f"eval skill_name must match an existing Skill and filename: {path}")
        if data.get("schema_version") != 1:
            _add(result, f"eval schema_version must be 1: {path}")
        if data.get("invocation_policy") not in {"explicit-only", "implicit-after-validation"}:
            _add(result, f"invalid eval invocation_policy: {path}")
        if data.get("validation_status") not in {"draft", "validated"}:
            _add(result, f"invalid eval validation_status: {path}")
        if data.get("side_effect_policy") not in {"instruction-only", "side-effectful"}:
            _add(result, f"invalid eval side_effect_policy: {path}")
        if not isinstance(data.get("unresolved_approval"), bool):
            _add(result, f"eval unresolved_approval must be boolean: {path}")
        for field_name in ("side_effect_boundary", "representative_dry_run", "false_positive_risk", "false_negative_risk", "stale_reference_risk"):
            _nonempty_string(data.get(field_name), field_name, path, result)
        for field_name in ("positive_triggers", "negative_triggers", "route_boundaries", "required_inputs", "expected_major_steps", "expected_outputs", "forbidden_actions"):
            if not _nonempty_strings(data.get(field_name), field_name, path, result):
                continue
            values = data[field_name]
            if field_name == "positive_triggers" and len(values) < 3:
                _add(result, f"positive_triggers must contain at least 3 prompts: {path}")
            if field_name == "negative_triggers" and len(values) < 2:
                _add(result, f"negative_triggers must contain at least 2 prompts: {path}")
        positives = data.get("positive_triggers", [])
        negatives = data.get("negative_triggers", [])
        if isinstance(positives, list) and sum(bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", item)) for item in positives if isinstance(item, str)) < max(2, len(positives) // 2 + 1):
            _add(result, f"positive_triggers must be Japanese-prompt centered: {path}")
        if isinstance(negatives, list) and sum(bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", item)) for item in negatives if isinstance(item, str)) < 1:
            _add(result, f"negative_triggers must include Japanese prompts: {path}")
        if (
            data.get("invocation_policy") == "implicit-after-validation"
            and isinstance(data.get("representative_dry_run"), str)
            and "metadata" not in data["representative_dry_run"]
        ):
            _add(result, f"implicit representative_dry_run must describe metadata routing: {path}")
        routing_cases = data.get("routing_cases")
        if not isinstance(routing_cases, list) or not routing_cases:
            _add(result, f"routing_cases must be a non-empty table list: {path}")
        else:
            required_case_keys = {
                "prompt", "expected_skills", "primary_skill", "automatic_chain", "permission_grant"
            }
            for case in routing_cases:
                if not isinstance(case, dict) or set(case) != required_case_keys:
                    _add(result, f"routing case keys are invalid: {path}")
                    continue
                if not isinstance(case["prompt"], str) or not case["prompt"].strip():
                    _add(result, f"routing case prompt must be non-empty: {path}")
                expected = case["expected_skills"]
                if (
                    not isinstance(expected, list)
                    or len(expected) < 2
                    or not all(isinstance(item, str) and item in skill_dirs for item in expected)
                ):
                    _add(result, f"routing case must name at least two existing Skills: {path}")
                if case["primary_skill"] not in expected:
                    _add(result, f"routing case primary_skill must be in expected_skills: {path}")
                if case["automatic_chain"] is not False:
                    _add(result, f"routing case must not require unconditional Skill chaining: {path}")
                if case["permission_grant"] is not False:
                    _add(result, f"routing case must not grant permissions: {path}")
        evals[str(name)] = data
    result.eval_count = len(paths)
    return evals


def _validate_implicit_activation(
    config: dict[str, Any],
    skill_dirs: dict[str, Path],
    evals: dict[str, dict[str, Any]],
    policies: dict[str, bool],
    candidates: dict[str, dict[str, Any]],
    result: ValidationResult,
) -> None:
    invocation = config.get("invocation", {})
    if invocation.get("validated_active_skill_default") != "implicit":
        _add(result, "validated active Skill default must remain implicit")
    if invocation.get("implicit_invocation_grants_permissions") is not False:
        _add(result, "implicit invocation permission grant must remain disabled")
    if set(evals) != set(skill_dirs):
        _add(result, "Skill and eval registries must not contain isolated entries")
    if set(policies) != set(skill_dirs):
        _add(result, "each Skill must have one valid policy entry")

    promotion_threshold = config.get("thresholds", {}).get("promotion_review")
    allowed_active_actions = invocation.get("active_candidate_actions", [])
    realized_by: dict[str, list[str]] = {}
    active_skills: set[str] = set()
    for candidate_key, candidate in candidates.items():
        realized = candidate.get("realized_by_skills", [])
        if not isinstance(realized, list):
            continue
        for skill_name in realized:
            if isinstance(skill_name, str):
                realized_by.setdefault(skill_name, []).append(candidate_key)
        if candidate.get("status") != "active":
            continue
        score = candidate.get("score")
        total = score.get("total") if isinstance(score, dict) else None
        if (
            isinstance(promotion_threshold, int)
            and isinstance(total, int)
            and total < promotion_threshold
        ):
            _add(
                result,
                f"active candidate score is below promotion_review threshold: {candidate_key}",
            )
        if candidate.get("proposed_action") not in allowed_active_actions:
            _add(result, f"active candidate action is not allowed by repository config: {candidate_key}")
        if not realized:
            _add(result, f"active candidate has no realized Skill: {candidate_key}")
        for skill_name in realized:
            if not isinstance(skill_name, str) or skill_name not in skill_dirs:
                continue
            active_skills.add(skill_name)
            eval_data = evals.get(skill_name, {})
            if eval_data.get("validation_status") != "validated":
                _add(result, f"active candidate Skill is not validated: {skill_name}")
            if eval_data.get("invocation_policy") != "implicit-after-validation":
                _add(result, f"active candidate Skill is not implicit-after-validation: {skill_name}")
            if eval_data.get("side_effect_policy") != "instruction-only":
                _add(result, f"active candidate Skill is not instruction-only: {skill_name}")
            if eval_data.get("unresolved_approval") is not False:
                _add(result, f"active candidate Skill has unresolved approval: {skill_name}")
            if policies.get(skill_name) is not True:
                _add(result, f"active candidate Skill must allow implicit invocation: {skill_name}")

    for skill_name, candidate_keys in realized_by.items():
        if len(candidate_keys) > 1:
            _add(
                result,
                f"Skill is realized by multiple candidates: {skill_name}: {sorted(candidate_keys)}",
            )
    for skill_name in sorted(set(skill_dirs) - set(realized_by)):
        _add(result, f"Skill is not traceable to a candidate: {skill_name}")

    implicit_skills = {name for name, value in policies.items() if value}
    for skill_name in sorted(implicit_skills - active_skills):
        _add(result, f"implicit Skill has no active candidate: {skill_name}")
    for skill_name in sorted(active_skills - implicit_skills):
        _add(result, f"active candidate must not realize an explicit-only Skill: {skill_name}")


def validate(root: Path = ROOT) -> ValidationResult:
    result = ValidationResult()
    agents_root = root / ".agents"
    if not agents_root.is_dir():
        _add(result, "repository-local .agents directory is missing")
        return result
    for path in sorted(agents_root.rglob("*")):
        if path.is_file():
            _read_text(path, result)
    config = _validate_config(root, result)
    if config is None:
        return result
    skill_dirs = _validate_skills(root, result, {})
    evals = _validate_evals(root, config, skill_dirs, result)
    policies: dict[str, bool] = {}
    for name, skill_dir in skill_dirs.items():
        value = _validate_skill_policy(skill_dir, evals.get(name), result)
        if value is not None:
            policies[name] = value
    candidates = _validate_candidates(root, config, result, set(skill_dirs))
    _validate_implicit_activation(config, skill_dirs, evals, policies, candidates, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate repository-local Codex Skill governance.")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)
    result = validate(args.root.resolve())
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(
        f"Agent Skill validation: skills={result.skill_count}, candidates={result.candidate_count}, "
        f"evals={result.eval_count}, errors={len(result.errors)}"
    )
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
