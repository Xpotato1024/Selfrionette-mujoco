"""S/G×画面力表示の自己pilot準備と、元trialを変更しない試行対応表。"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite, sqrt
import os
from pathlib import Path
import re
import stat

from xpotato_sim.runtime.experiment.edited_condition import resolve_condition, MAX_BYTES
from xpotato_sim.runtime.experiment.trial_condition import semantic_parameters
from xpotato_sim.runtime.scene.objects import canonical, fields, strict_json

CONDITIONS = ("g_off", "s_off", "g_on", "s_on")
# 4行全体で位置と直前条件を釣り合わせる。1人の1行だけを完全相殺とは呼ばない。
ORDER_ROWS = ((0, 1, 3, 2), (1, 2, 0, 3), (2, 3, 1, 0), (3, 0, 2, 1))
SESSION_SCHEMA = "pilot-session/v1"
MAX_SESSION_BYTES = 1024 * 1024
MAX_RECORD_BYTES = 16384


def _identifier(value, label):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value) is None:
        raise ValueError(f"{label}: 1..64文字の匿名英数字IDが必要です")
    return value


def _bounded_text(value, label, maximum=2048):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label}: 空でない{maximum}文字以内の記述が必要です")
    return value


def read_condition(path):
    with Path(path).open("rb") as stream:
        return resolve_condition(stream.read(MAX_BYTES + 1))[2]


def _read_file(path, bound):
    """固定名のregular fileだけを有界に読み、参照先の差替えを受理しない。"""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > bound:
        raise ValueError("bounded regular pilot file required")
    with path.open("rb") as stream:
        data = stream.read(bound + 1)
    if len(data) > bound:
        raise ValueError("pilot file exceeds byte bound")
    return data


def _write_new(path, value):
    """新規ファイルだけを作る。session.jsonの存在が準備完了の目印。"""
    data = canonical(value) + b"\n"
    pending = path.with_name(path.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if pending.read_bytes() != data:
        raise OSError("pilot file read-back mismatch")
    os.link(pending, path)
    try:
        pending.unlink()
    except OSError:
        pass
    return {"file": path.name, "sha256": sha256(data).hexdigest()}


def _fixture_identity(document):
    parameters = document["configuration"]["input"]["parameters"]
    sentinel = "0123456789abcdef0123456789abcdef01234567"
    known_devices = {"srn-0123456789abcdef0123456789abcdef", "srn-fedcba9876543210fedcba9876543210"}
    return (parameters["bridge_revision"] == sentinel or any(
        binding["source"]["device_id"] in known_devices
        or binding["source"]["source_sha"] == sentinel
        or binding["operator"]["operator"].startswith("fixture")
        for binding in parameters["bindings"].values()))


def comparison_conditions(gamepad, selfrionette, *, speed_m_s, software_fixture):
    """同じworld/Taskから4条件を作る。入力固有の校正や重みを推測しない。"""
    if type(speed_m_s) not in (int, float) or not isfinite(speed_m_s) or speed_m_s <= 0:
        raise ValueError("共通の正の有限速度係数 speed_m_s が必要です")
    if type(software_fixture) is not bool:
        raise ValueError("software_fixtureは明示的なboolが必要です")
    g, s = (resolve_condition(deepcopy(v))[2] for v in (gamepad, selfrionette))
    if g["configuration"]["input"]["provider"] != "gamepad/v1" or s["configuration"]["input"]["provider"] != "selfrionette-device/v1":
        raise ValueError("GamepadとSelfrionetteの条件をそれぞれ明示してください")
    if g["configuration"]["mapping"]["plugin"]["name"] != "viewer_keyboard_gamepad_mapping" or s["configuration"]["mapping"]["plugin"]["name"] != "normalized_endpoint_velocity":
        raise ValueError("共通rate比較に対応するMappingが必要です")
    if not software_fixture and _fixture_identity(s):
        raise ValueError("Selfrionetteのfixture identityは実操作者用sessionに使用できません")
    for key in ("preset_id", "model_configuration_sha256", "environment", "task", "evaluation", "limits", "command_mapping"):
        if g[key] != s[key]:
            raise ValueError(f"比較する共通条件が一致しません: {key}")
    for key in ("robot", "model", "coordination", "execution"):
        if g["configuration"][key] != s["configuration"][key]:
            raise ValueError(f"比較する共通条件が一致しません: configuration.{key}")
    for d in (g, s):
        if d["display_comparison"] is None:
            raise ValueError("明示的な画面力表示条件が必要です")
    if {k: v for k, v in g["display_comparison"].items() if k != "mode"} != {k: v for k, v in s["display_comparison"].items() if k != "mode"}:
        raise ValueError("画面力表示の縮尺・飽和・有効期間が一致しません")
    gp = g["configuration"]["mapping"]["parameters"]
    sp = s["configuration"]["mapping"]["parameters"]
    if sp["control_frame"] != "world":
        raise ValueError("この準備入口はworld座標の共通rate比較に限定しています")
    if any(sum(abs(row[axis]) for row in rows) > 1
           for rows in sp["channel_axis_weights"].values() for axis in range(3)):
        raise ValueError("共通速度範囲には各出力axisのabsolute weight sum <= 1が必要です。重みは自動変更しません")
    gp["gamepad_speed_m_s"] = float(speed_m_s)
    sp["speed_m_s"] = float(speed_m_s)
    # 単位入力を3軸同時に与えた範囲で、Sだけ追加norm飽和しない上限を明記する。
    sp["max_speed_m_s"] = sqrt(3) * float(speed_m_s)
    if gp["gamepad_max_delta_m"] < sqrt(3) * speed_m_s * g["configuration"]["execution"]["dt_s"]:
        raise ValueError("Gamepadのdelta上限が共通速度範囲より小さいため、元条件を見直してください")
    conditions = {}
    for name, base in (("g_off", g), ("s_off", s), ("g_on", g), ("s_on", s)):
        candidate = deepcopy(base)
        candidate["display_comparison"]["mode"] = "force_cue" if name.endswith("on") else "no_force_cue"
        profile, limits, normalized = resolve_condition(candidate)
        conditions[name] = {"document": normalized,
            "semantic_condition": json.loads(canonical(semantic_parameters(profile, limits)))}
    return conditions


def _readiness():
    return {"hardware_verified": False, "research_protocol_frozen": False,
        "additional_haptic_device": "frozen", "task_selection": "operator_defined",
        "note": "条件準備だけでは実機校正・課題採択・人数・主指標の確定を意味しません"}


def create_session(*, gamepad, selfrionette, output, participant_id, session_id,
                   repetitions, order_row, speed_m_s, software_revision,
                   software_fixture, protocol_note):
    """条件と順序を排他的に保存する。接続・開始・本実験の採択は行わない。"""
    _identifier(participant_id, "participant_id")
    _identifier(session_id, "session_id")
    _bounded_text(software_revision, "software_revision", 256)
    _bounded_text(protocol_note, "protocol_note")
    if type(repetitions) is not int or not 1 <= repetitions <= 100:
        raise ValueError("repetitionsは1..100です")
    if type(order_row) is not int or not 0 <= order_row < 4:
        raise ValueError("order_rowは0..3です")
    conditions = comparison_conditions(gamepad, selfrionette, speed_m_s=speed_m_s, software_fixture=software_fixture)
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    entries = {}
    for name in CONDITIONS:
        value = conditions[name]
        entries[name] = {**_write_new(root / f"{name}.json", value["document"]),
                         "semantic_condition": value["semantic_condition"]}
    trials = []
    for repetition in range(repetitions):
        row = (order_row + repetition) % 4
        for index in ORDER_ROWS[row]:
            trials.append({"slot": len(trials) + 1, "repetition": repetition + 1,
                           "order_row": row, "condition_id": CONDITIONS[index]})
    document = {"schema_version": SESSION_SCHEMA, "session_id": session_id,
        "participant_id": participant_id, "software_revision": software_revision,
        "usage": "software_validation" if software_fixture else "operator_pilot",
        "speed_m_s": float(speed_m_s), "repetitions": repetitions, "order_row": order_row,
        "protocol_note": protocol_note, "conditions": entries, "trials": trials,
        "readiness": _readiness()}
    _write_new(root / "session.json", document)
    return document


def load_session(path):
    """全条件の参照hashと意味条件を照合する。相対参照は固定ファイル名だけ。"""
    path = Path(path).absolute()
    data = _read_file(path, MAX_SESSION_BYTES)
    document = fields(strict_json(data, max_bytes=MAX_SESSION_BYTES), {
        "schema_version", "session_id", "participant_id", "software_revision", "usage",
        "speed_m_s", "repetitions", "order_row", "protocol_note", "conditions", "trials", "readiness",
    }, "pilot session")
    if document["schema_version"] != SESSION_SCHEMA:
        raise ValueError("pilot-session/v1 required")
    _identifier(document["session_id"], "session_id")
    _identifier(document["participant_id"], "participant_id")
    _bounded_text(document["software_revision"], "software_revision", 256)
    _bounded_text(document["protocol_note"], "protocol_note")
    if type(document["usage"]) is not str or document["usage"] not in {"software_validation", "operator_pilot"}:
        raise ValueError("invalid pilot usage")
    fields(document["conditions"], set(CONDITIONS), "exactly four pilot conditions required")
    if canonical(document["readiness"]) != canonical(_readiness()):
        raise ValueError("pilot preparation cannot certify hardware or research protocol readiness")
    normalized = {}
    for name, entry in document["conditions"].items():
        fields(entry, {"file", "sha256", "semantic_condition"}, "pilot condition reference")
        if entry["file"] != f"{name}.json":
            raise ValueError("invalid pilot condition reference")
        file = path.parent / entry["file"]
        raw = _read_file(file, MAX_BYTES)
        if sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("pilot condition digest mismatch")
        profile, limits, normalized[name] = resolve_condition(raw)
        if canonical(semantic_parameters(profile, limits)) != canonical(entry["semantic_condition"]):
            raise ValueError("pilot semantic condition mismatch")
    expected = comparison_conditions(normalized["g_off"], normalized["s_off"],
        speed_m_s=document["speed_m_s"], software_fixture=document["usage"] == "software_validation")
    if any(canonical(expected[name]["document"]) != canonical(normalized[name]) for name in CONDITIONS):
        raise ValueError("pilot factorial conditions mismatch")
    repetitions, first = document["repetitions"], document["order_row"]
    if type(repetitions) is not int or not 1 <= repetitions <= 100 or type(first) is not int or not 0 <= first < 4:
        raise ValueError("invalid bounded pilot schedule")
    expected_trials = [{"slot": rep * 4 + pos + 1, "repetition": rep + 1,
        "order_row": (first + rep) % 4, "condition_id": CONDITIONS[index]}
        for rep in range(repetitions) for pos, index in enumerate(ORDER_ROWS[(first + rep) % 4])]
    if canonical(document["trials"]) != canonical(expected_trials):
        raise ValueError("pilot schedule mismatch")
    return document, sha256(data).hexdigest()


def validate_planned_trial(session, *, slot, analysis):
    """検証済みtrialの実条件・版・入力来歴を予定slotへ照合する。"""
    if type(slot) is not int or not 1 <= slot <= len(session["trials"]):
        raise ValueError("unknown pilot slot")
    selected = session["trials"][slot - 1]
    expected = session["conditions"][selected["condition_id"]]["semantic_condition"]
    actual = deepcopy(analysis["condition"])
    if actual.get("display_comparison") is not None:
        actual["display_comparison"] = actual["display_comparison"]["presentation"]
    if any(key not in actual or canonical(actual[key]) != canonical(value) for key, value in expected.items()):
        raise ValueError("trial condition differs from the planned slot")
    if analysis["software_revision"] != session["software_revision"]:
        raise ValueError("trial software revision differs from session")
    if session["usage"] == "operator_pilot":
        display = analysis["condition"].get("display_comparison")
        provenance = analysis["input_provenance"]
        source = {"gamepad/v1": "workbench-gamepad/v1", "selfrionette-device/v1": "selfrionette-bridge/v1"}[expected["input"]["provider"]]
        if not display or display["viewer"]["mode"] != "production" or provenance.get("source") != source:
            raise ValueError("operator pilot requires production viewer and live-input provenance")
    return selected


def attach_trial(*, session_path, slot, trial_directory, attempt=1, retry_reason=None, response=None):
    """完了済みtrialを予定slotへ対応付け、失敗・再試行も別記録として残す。"""
    from xpotato_sim.runtime.experiment.trial_analysis import load_validated_trial
    session_path = Path(session_path).absolute()
    session, digest = load_session(session_path)
    if type(slot) is not int or not 1 <= slot <= len(session["trials"]):
        raise ValueError("unknown pilot slot")
    if type(attempt) is not int or not 1 <= attempt <= 100:
        raise ValueError("attemptは1..100です")
    if attempt > 1:
        _bounded_text(retry_reason, "retry_reason")
    elif retry_reason is not None:
        raise ValueError("最初の試行にretry_reasonは指定できません")
    trial = load_validated_trial(trial_directory)
    analysis = trial.analysis()
    selected = validate_planned_trial(session, slot=slot, analysis=analysis)
    if response is not None:
        if type(response) is not dict or len(canonical(response)) > 8192:
            raise ValueError("responseは8192 bytes以内のJSON objectです")
        response = strict_json(canonical(response))
    records = session_path.parent / "records"
    if records.is_symlink():
        raise ValueError("pilot records must not be a symlink")
    records.mkdir(exist_ok=True)
    previous = records / f"slot-{slot:03d}-attempt-{attempt-1:03d}.json"
    if attempt > 1 and not previous.is_file():
        raise ValueError("再試行前のattempt記録が必要です")
    if attempt > 1:
        prior = strict_json(_read_file(previous, MAX_RECORD_BYTES), max_bytes=MAX_RECORD_BYTES)
        if (prior.get("session_sha256") != digest or prior.get("slot") != slot
                or type(prior.get("attempt")) is not int or prior["attempt"] != attempt - 1
                or any(prior.get(key) != value for key, value in selected.items())):
            raise ValueError("previous attempt identity mismatch")
    existing = list(records.glob("slot-*-attempt-*.json"))
    if len(existing) > 40000:
        raise ValueError("pilot record bound exceeded")
    for record in existing:
        old = strict_json(_read_file(record, MAX_RECORD_BYTES), max_bytes=MAX_RECORD_BYTES)
        if old.get("schema_version") != "pilot-trial-link/v1" or old.get("session_sha256") != digest:
            raise ValueError("existing pilot record identity mismatch")
        if old.get("trial_id") == analysis["trial_id"]:
            raise ValueError("trial is already attached; repeated samples are not new trials")
    value = {"schema_version": "pilot-trial-link/v1", "session_sha256": digest,
        "session_id": session["session_id"], "participant_id": session["participant_id"],
        **selected, "attempt": attempt, "retry_reason": retry_reason,
        "trial_id": analysis["trial_id"], "epoch": analysis["epoch"],
        "condition_sha256": analysis["condition_sha256"],
        "terminal_sha256": analysis["terminal_sha256"],
        "trial_directory": str(Path(trial_directory).resolve()),
        "runner_stop_reason": analysis["runner_stop_reason"], "response": response}
    if len(canonical(value)) + 1 > MAX_RECORD_BYTES:
        raise ValueError("pilot trial link exceeds byte bound")
    _write_new(records / f"slot-{slot:03d}-attempt-{attempt:03d}.json", value)
    return value
