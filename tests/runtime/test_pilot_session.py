"""4条件の準備と保存trialの対応付けを検証する。実機・被験者の受入ではない。"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path

import pytest

from xpotato_sim.runtime.experiment import pilot_session as pilot
from xpotato_sim.runtime.experiment.edited_condition import preset_condition, resolve_condition
from xpotato_sim.runtime.experiment.trial_analysis import load_validated_trial
from xpotato_sim.runtime.experiment.trial_runner import TrialRunner
from xpotato_sim.runtime.scene.objects import canonical
from tests.runtime.test_trial_runner import Clock
from tests.runtime.test_research_spring_demo import run


def conditions():
    g = preset_condition("tasks/research-spring", input_provider="gamepad/v1")
    s = preset_condition("tasks/research-spring", input_provider="selfrionette-device/v1")
    g["limits"]["max_ticks"] = s["limits"]["max_ticks"] = 4
    return g, s


def arguments(root, *, software_fixture=True):
    g, s = conditions()
    if not software_fixture:
        # 予約fixture値だけを除いた検査用identity。実機の個体・校正証拠ではない。
        parameters = s["configuration"]["input"]["parameters"]
        parameters["bridge_revision"] = "a" * 40
        binding = parameters["bindings"]["left"]
        binding["source"].update(device_id="srn-" + "1" * 32, source_sha="b" * 40)
        binding["operator"]["operator"] = "unverified-test-identity"
    return dict(gamepad=g, selfrionette=s, output=root, participant_id="p01",
        session_id="pilot01", repetitions=1, order_row=0, speed_m_s=.03,
        software_revision="software-test-only", software_fixture=software_fixture,
        protocol_note="自己pilot準備のsoftware検証。研究protocolと実機条件は未承認。")


@pytest.fixture
def session(tmp_path):
    root = tmp_path / "session"
    document = pilot.create_session(**arguments(root))
    return root, document


def record(root, condition, *, revision="software-test-only", failure=False):
    profile, limits, _ = resolve_condition(condition)
    clock = Clock()
    runner = TrialRunner(result_root=root, software_revision=revision, clock=clock)
    ticket = runner.prepare(profile, limits)
    try:
        if failure:
            runner.start(ticket, input_provenance={"source": "software-validation-fixture"})
            runner.fail(ticket, "explicit software fault")
        else:
            run(runner, ticket, clock)
    finally:
        runner.close()
    return root / ticket.trial_id


def read(path):
    return json.loads(path.read_bytes())


def write(path, document):
    path.write_bytes(canonical(document) + b"\n")


def test_four_conditions_share_physics_and_freeze_requested_rate_without_mutating_inputs():
    g, s = conditions()
    before = deepcopy((g, s))
    s["configuration"]["mapping"]["parameters"]["channel_axis_weights"]["left"][0][0] = .5
    weights = deepcopy(s["configuration"]["mapping"]["parameters"]["channel_axis_weights"])
    values = pilot.comparison_conditions(g, s, speed_m_s=.04, software_fixture=True)
    assert set(values) == set(pilot.CONDITIONS)
    assert g == before[0]
    assert s["configuration"]["mapping"]["parameters"]["speed_m_s"] == before[1]["configuration"]["mapping"]["parameters"]["speed_m_s"]
    for key, value in values.items():
        document = value["document"]
        assert document["environment"] == g["environment"]
        assert document["task"] == g["task"]
        assert document["display_comparison"]["mode"] == ("force_cue" if key.endswith("on") else "no_force_cue")
        parameters = document["configuration"]["mapping"]["parameters"]
        if key.startswith("s"):
            assert parameters["speed_m_s"] == .04
            assert parameters["max_speed_m_s"] == sqrt(3) * .04
            assert parameters["channel_axis_weights"] == weights
        else:
            assert parameters["gamepad_speed_m_s"] == .04
    for provider in ("g", "s"):
        off = deepcopy(values[provider + "_off"]["document"])
        on = deepcopy(values[provider + "_on"]["document"])
        off["display_comparison"]["mode"] = on["display_comparison"]["mode"]
        assert off == on


@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf")])
def test_invalid_common_rate_is_rejected(value):
    with pytest.raises(ValueError):
        pilot.comparison_conditions(*conditions(), speed_m_s=value, software_fixture=True)


@pytest.mark.parametrize("change", [
    lambda g, s: s["limits"].update(max_ticks=5),
    lambda g, s: s["display_comparison"].update(scale_m_per_n=.003),
    lambda g, s: s["configuration"]["mapping"]["parameters"].update(control_frame="tool"),
    lambda g, s: g["configuration"]["mapping"]["parameters"].update(gamepad_max_delta_m=.00001),
    lambda g, s: s["configuration"]["mapping"]["parameters"]["channel_axis_weights"]["left"][3].__setitem__(0, .01),
])
def test_incomparable_limits_display_frame_or_clipping_require_explicit_revision(change):
    g, s = conditions()
    change(g, s)
    with pytest.raises(ValueError):
        pilot.comparison_conditions(g, s, speed_m_s=.04, software_fixture=True)


def test_known_fixture_identity_cannot_become_operator_pilot(tmp_path):
    args = arguments(tmp_path / "rejected")
    args["software_fixture"] = False
    with pytest.raises(ValueError, match="fixture identity"):
        pilot.create_session(**args)
    assert not args["output"].exists()
    args["software_fixture"] = "false"
    with pytest.raises(ValueError, match="bool"):
        pilot.create_session(**args)


def test_schedule_has_balanced_positions_and_predecessors_across_all_four_rows(tmp_path):
    args = arguments(tmp_path / "session")
    args.update(repetitions=4, order_row=2)
    document = pilot.create_session(**args)
    trials = document["trials"]
    assert [trial["slot"] for trial in trials] == list(range(1, 17))
    blocks = [trials[i:i+4] for i in range(0, 16, 4)]
    for position in range(4):
        assert {block[position]["condition_id"] for block in blocks} == set(pilot.CONDITIONS)
    pairs = Counter((a["condition_id"], b["condition_id"]) for block in blocks for a, b in zip(block, block[1:]))
    assert len(pairs) == 12 and set(pairs.values()) == {1}
    loaded, digest = pilot.load_session(args["output"] / "session.json")
    assert loaded == document
    assert digest == sha256((args["output"] / "session.json").read_bytes()).hexdigest()
    assert document["readiness"]["hardware_verified"] is False
    assert document["readiness"]["research_protocol_frozen"] is False


def test_existing_session_is_unchanged_on_recreate(session):
    root, _ = session
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    with pytest.raises(FileExistsError):
        pilot.create_session(**arguments(root))
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_interrupted_final_save_leaves_no_completed_session(tmp_path, monkeypatch):
    root = tmp_path / "session"
    fsync = pilot.os.fsync
    calls = 0
    def fail_last(fd):
        nonlocal calls
        calls += 1
        if calls == 5:
            raise OSError("injected final-session fsync failure")
        return fsync(fd)
    monkeypatch.setattr(pilot.os, "fsync", fail_last)
    with pytest.raises(OSError, match="injected"):
        pilot.create_session(**arguments(root))
    assert not (root / "session.json").exists()
    assert (root / "session.json.pending").exists()
    with pytest.raises(FileNotFoundError):
        pilot.load_session(root / "session.json")


@pytest.mark.parametrize("change", [
    lambda d: d["conditions"]["g_off"].update(file="../g_off.json"),
    lambda d: d["conditions"]["g_off"].update(sha256="0" * 64),
    lambda d: d["conditions"]["g_off"]["semantic_condition"].update(dt_s=.5),
    lambda d: d["trials"][0].update(condition_id="s_off"),
    lambda d: d["trials"][0].update(slot=True),
    lambda d: d["readiness"].update(hardware_verified=True),
    lambda d: d["readiness"].update(research_protocol_frozen=True),
    lambda d: d.update(protocol_note=""),
    lambda d: d.update(software_revision=[]),
    lambda d: d.update(repetitions=True),
    lambda d: d.update(extra="unknown"),
    lambda d: d.pop("participant_id"),
])
def test_changed_session_metadata_conditions_or_schedule_are_rejected(session, change):
    root, document = session
    change(document)
    write(root / "session.json", document)
    with pytest.raises(ValueError):
        pilot.load_session(root / "session.json")


def test_rehashing_on_condition_does_not_hide_factorial_difference(session):
    root, document = session
    path = root / "g_on.json"
    value = read(path)
    value["limits"]["max_ticks"] = 3
    profile, limits, value = resolve_condition(value)
    write(path, value)
    document["conditions"]["g_on"]["sha256"] = sha256(path.read_bytes()).hexdigest()
    document["conditions"]["g_on"]["semantic_condition"] = pilot.semantic_parameters(profile, limits)
    write(root / "session.json", document)
    with pytest.raises(ValueError, match="factorial"):
        pilot.load_session(root / "session.json")


def test_reference_symlink_cannot_redirect_condition(session, tmp_path):
    root, _ = session
    path = root / "g_off.json"
    outside = tmp_path / "outside-condition.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"OS does not permit creating symlinks: {error}")
    with pytest.raises(ValueError, match="regular"):
        pilot.load_session(root / "session.json")


def test_real_trial_attach_preserves_original_and_freezes_terminal_digest(session, tmp_path):
    root, _ = session
    trial = record(tmp_path / "trials", read(root / "g_off.json"))
    before = {path.name: path.read_bytes() for path in trial.iterdir()}
    link = pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=trial,
        response={"felt_resistance": 2, "note": "software fixture response"})
    assert link["condition_id"] == "g_off" and link["attempt"] == 1
    assert link["terminal_sha256"] == sha256((trial / "terminal.json").read_bytes()).hexdigest()
    assert link["runner_stop_reason"] == "simulation_budget"
    assert {path.name: path.read_bytes() for path in trial.iterdir()} == before
    with pytest.raises(ValueError, match="already attached"):
        pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=trial)


@pytest.mark.parametrize("slot,revision", [(2, "software-test-only"), (4, "software-test-only"), (1, "other-source")])
def test_trial_cannot_be_attached_to_other_input_display_or_revision(session, tmp_path, slot, revision):
    root, _ = session
    trial = record(tmp_path / "trials", read(root / "g_off.json"), revision=revision)
    with pytest.raises(ValueError, match="differs"):
        pilot.attach_trial(session_path=root / "session.json", slot=slot, trial_directory=trial)
    assert not (root / "records").exists()


def test_retry_retains_failed_trial_and_requires_reason_and_previous_attempt(session, tmp_path):
    root, _ = session
    first = record(tmp_path / "trials", read(root / "g_off.json"), failure=True)
    second = record(tmp_path / "trials", read(root / "g_off.json"))
    options = dict(session_path=root / "session.json", slot=1, trial_directory=second, attempt=2)
    with pytest.raises(ValueError, match="retry_reason"):
        pilot.attach_trial(**options)
    with pytest.raises(ValueError, match="attempt"):
        pilot.attach_trial(**options, retry_reason="software fault recovery")
    first_link = pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=first)
    assert first_link["runner_stop_reason"] == "technical_invalid"
    previous = (root / "records/slot-001-attempt-001.json").read_bytes()
    second_link = pilot.attach_trial(**options, retry_reason="software fault recovery")
    assert first_link["trial_id"] != second_link["trial_id"]
    assert (root / "records/slot-001-attempt-001.json").read_bytes() == previous


def test_tampered_retry_slot_identity_is_rejected(session, tmp_path):
    root, _ = session
    first = record(tmp_path / "trials", read(root / "g_off.json"), failure=True)
    second = record(tmp_path / "trials", read(root / "g_off.json"))
    pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=first)
    path = root / "records/slot-001-attempt-001.json"
    value = read(path)
    value["condition_id"] = "s_on"
    write(path, value)
    with pytest.raises(ValueError, match="previous attempt"):
        pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=second,
            attempt=2, retry_reason="software fault recovery")


def test_retry_response_and_reason_together_cannot_make_an_unreadable_record(session, tmp_path):
    root, _ = session
    first = record(tmp_path / "trials", read(root / "g_off.json"), failure=True)
    second = record(tmp_path / "trials", read(root / "g_off.json"))
    pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=first)
    with pytest.raises(ValueError, match="byte bound"):
        pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=second,
            attempt=2, retry_reason="😀" * 2048, response={"note": "a" * 8000})
    assert not (root / "records/slot-001-attempt-002.json").exists()


@pytest.mark.parametrize("provider,wrong", [
    ("g_off", "selfrionette-bridge/v1"), ("s_off", "workbench-gamepad/v1"),
])
def test_operator_pilot_rejects_swapped_live_provenance(tmp_path, monkeypatch, provider, wrong):
    root = tmp_path / "session"
    session = pilot.create_session(**arguments(root, software_fixture=False))
    condition = deepcopy(session["conditions"][provider]["semantic_condition"])
    condition["display_comparison"] = {"presentation": condition["display_comparison"],
        "viewer": {"mode": "production", "source_sha256": "1" * 64, "build_sha256": "2" * 64}}
    # 記録decoderの後にあるsource照合だけを検査する。実viewer/実入力とは扱わない。
    class MetadataFixture:
        def analysis(self):
            return {"condition": condition, "software_revision": "software-test-only",
                "input_provenance": {"source": wrong}}
    monkeypatch.setattr("xpotato_sim.runtime.experiment.trial_analysis.load_validated_trial", lambda _: MetadataFixture())
    slot = 1 if provider == "g_off" else 2
    with pytest.raises(ValueError, match="live-input provenance"):
        pilot.attach_trial(session_path=root / "session.json", slot=slot, trial_directory=tmp_path / "unread")


def test_operator_pilot_cannot_attach_headless_software_trial(tmp_path):
    root = tmp_path / "session"
    pilot.create_session(**arguments(root, software_fixture=False))
    trial = record(tmp_path / "trials", read(root / "g_off.json"))
    assert load_validated_trial(trial).analysis()["condition"]["display_comparison"]["viewer"]["mode"] == "headless"
    with pytest.raises(ValueError, match="production viewer"):
        pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=trial)
