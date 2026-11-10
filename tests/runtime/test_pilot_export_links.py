"""保存trialが有効でも、予定条件への誤対応をverifiedへ昇格させない。"""
from hashlib import sha256

import pytest

from tests.runtime.test_pilot_session import arguments, read, record, write
from tests.runtime.test_trial_runner import Clock
from xpotato_sim.runtime.experiment import pilot_session as pilot
from xpotato_sim.runtime.experiment.edited_condition import resolve_condition
from xpotato_sim.runtime.experiment.pilot_export import export_results
from xpotato_sim.runtime.experiment.trial_analysis import load_validated_trial
from xpotato_sim.runtime.experiment.trial_runner import TrialRunner


@pytest.fixture
def linked(tmp_path):
    root = tmp_path / "session"
    document = pilot.create_session(**arguments(root))
    trial = record(tmp_path / "trials", read(root / "g_off.json"))
    link = pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=trial)
    return root, document, trial, link


def export(root, trial, output):
    return export_results(result_root=trial.parent, output=output,
        session_path=root / "session.json", plots=False)


def test_valid_link_is_preserved(linked, tmp_path):
    root, _, trial, link = linked
    report = export(root, trial, tmp_path / "export")
    assert report["verified_count"] == 1
    assert report["invalid_or_incomplete_count"] == 0
    assert report["trials"][0]["pilot_link"] == link


@pytest.mark.parametrize("slot", [2, 4])
def test_relabeling_valid_trial_as_other_input_or_display_is_rejected(linked, tmp_path, slot):
    root, document, trial, link = linked
    # schedule、固定名、trialのhashが各々整合しても、実条件との一致が必要。
    link.update(document["trials"][slot - 1])
    (root / "records" / "slot-001-attempt-001.json").unlink()
    write(root / "records" / f"slot-{slot:03d}-attempt-001.json", link)
    actual = load_validated_trial(trial).analysis()
    assert actual["condition_sha256"] == link["condition_sha256"]
    assert actual["terminal_sha256"] == link["terminal_sha256"]
    report = export(root, trial, tmp_path / "export")
    assert report["verified_count"] == 0
    assert report["invalid_or_incomplete_count"] == 1
    assert "trial condition differs" in report["invalid_or_incomplete"][0]["error"]


def test_export_rechecks_trial_revision_against_session(linked, tmp_path):
    root, document, trial, link = linked
    document["software_revision"] = "other-expected-software"
    write(root / "session.json", document)
    link["session_sha256"] = sha256((root / "session.json").read_bytes()).hexdigest()
    write(root / "records" / "slot-001-attempt-001.json", link)
    assert load_validated_trial(trial).analysis()["software_revision"] == "software-test-only"
    report = export(root, trial, tmp_path / "export")
    assert report["verified_count"] == 0
    assert "software revision differs" in report["invalid_or_incomplete"][0]["error"]


@pytest.mark.parametrize("condition_id,viewer,source", [
    ("g_off", "headless", "workbench-gamepad/v1"),
    ("g_off", "production", "selfrionette-bridge/v1"),
    ("s_off", "production", "workbench-gamepad/v1"),
])
def test_operator_export_rechecks_viewer_and_provider_specific_source(tmp_path, condition_id, viewer, source):
    software_root, operator_root = tmp_path / "software", tmp_path / "operator"
    software_args = arguments(software_root, software_fixture=False)
    software_args["software_fixture"] = True
    pilot.create_session(**software_args)
    document = pilot.create_session(**arguments(operator_root, software_fixture=False))
    profile, limits, _ = resolve_condition(read(operator_root / f"{condition_id}.json"))
    # productionという値の照合用fixtureであり、実Viewer・実入力の証拠ではない。
    viewer_identity = None if viewer == "headless" else {
        "mode": "production", "source_sha256": "1" * 64, "build_sha256": "2" * 64}
    runner = TrialRunner(result_root=tmp_path / "trials", software_revision="software-test-only",
        clock=Clock(), viewer_build_identity=viewer_identity)
    ticket = runner.prepare(profile, limits)
    try:
        runner.start(ticket, input_provenance={"source": source, "fixture": "metadata-only"})
        runner.abort(ticket)
    finally:
        runner.close()
    trial = tmp_path / "trials" / ticket.trial_id
    slot = next(item["slot"] for item in document["trials"] if item["condition_id"] == condition_id)
    link = pilot.attach_trial(session_path=software_root / "session.json", slot=slot, trial_directory=trial)
    link["session_sha256"] = sha256((operator_root / "session.json").read_bytes()).hexdigest()
    (operator_root / "records").mkdir()
    write(operator_root / "records" / f"slot-{slot:03d}-attempt-001.json", link)
    assert load_validated_trial(trial).analysis()["input_provenance"]["source"] == source
    report = export(operator_root, trial, tmp_path / "export")
    assert report["verified_count"] == 0
    assert report["invalid_or_incomplete_count"] == 1
    assert "production viewer and live-input provenance" in report["invalid_or_incomplete"][0]["error"]


@pytest.mark.parametrize("attempt", [True, 0, 101, 1.5, "1"])
def test_invalid_attempt_is_rejected_before_creating_output(linked, tmp_path, attempt):
    root, _, trial, link = linked
    link["attempt"] = attempt
    write(root / "records" / "slot-001-attempt-001.json", link)
    with pytest.raises(ValueError, match="attempt must"):
        export(root, trial, tmp_path / "export")
    assert not (tmp_path / "export").exists()


@pytest.mark.parametrize("key,value", [("repetition", True), ("order_row", False)])
def test_schedule_boolean_cannot_match_integer(linked, tmp_path, key, value):
    root, _, trial, link = linked
    link[key] = value
    write(root / "records" / "slot-001-attempt-001.json", link)
    with pytest.raises(ValueError, match="schedule mismatch"):
        export(root, trial, tmp_path / "export")


@pytest.mark.parametrize("attempt,reason,match", [
    (1, "invented retry", "first pilot attempt"),
    (2, None, "bounded reason"),
    (2, " ", "bounded reason"),
    (2, "x" * 2049, "bounded reason"),
    (2, "explicit retry", "previous attempt"),
])
def test_retry_reason_and_previous_record_are_required(linked, tmp_path, attempt, reason, match):
    root, _, trial, link = linked
    (root / "records" / "slot-001-attempt-001.json").unlink()
    link.update(attempt=attempt, retry_reason=reason)
    write(root / "records" / f"slot-001-attempt-{attempt:03d}.json", link)
    with pytest.raises(ValueError, match=match):
        export(root, trial, tmp_path / "export")
    assert not (tmp_path / "export").exists()


def test_valid_retry_preserves_failed_first_attempt(tmp_path):
    root = tmp_path / "session"
    pilot.create_session(**arguments(root))
    first = record(tmp_path / "trials", read(root / "g_off.json"), failure=True)
    second = record(tmp_path / "trials", read(root / "g_off.json"))
    pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=first)
    pilot.attach_trial(session_path=root / "session.json", slot=1, trial_directory=second,
        attempt=2, retry_reason="software fault recovery")
    report = export(root, second, tmp_path / "export")
    assert report["verified_count"] == 2 and report["invalid_or_incomplete_count"] == 0
    assert {trial["pilot_link"]["attempt"] for trial in report["trials"]} == {1, 2}
    assert report["stop_reasons"] == {"technical_invalid": 1, "simulation_budget": 1}


def test_link_filename_must_match_record_identity(linked, tmp_path):
    root, _, trial, _ = linked
    (root / "records" / "slot-001-attempt-001.json").rename(root / "records" / "slot-002-attempt-001.json")
    with pytest.raises(ValueError, match="filename differs"):
        export(root, trial, tmp_path / "export")


def test_duplicate_slot_attempt_cannot_add_another_link(linked, tmp_path):
    root, _, trial, link = linked
    link["trial_id"] = "other-trial-identity"
    write(root / "records" / "slot-001-attempt-001x.json", link)
    with pytest.raises(ValueError, match="duplicate pilot slot attempt"):
        export(root, trial, tmp_path / "export")


@pytest.mark.parametrize("target", ["record", "records-directory"])
def test_record_symlink_cannot_redirect_session_links(linked, tmp_path, target):
    root, _, trial, _ = linked
    path = root / "records"
    if target == "record":
        path /= "slot-001-attempt-001.json"
    outside = tmp_path / "redirected"
    path.rename(outside)
    try:
        path.symlink_to(outside, target_is_directory=target == "records-directory")
    except OSError as error:
        pytest.skip(f"OS does not permit creating symlinks: {error}")
    with pytest.raises(ValueError, match="regular"):
        export(root, trial, tmp_path / "export")
    assert not (tmp_path / "export").exists()


def test_oversized_link_is_rejected_before_parsing(linked, tmp_path):
    root, _, trial, _ = linked
    (root / "records" / "slot-001-attempt-001.json").write_bytes(b" " * (pilot.MAX_RECORD_BYTES + 1))
    with pytest.raises(ValueError, match="bounded regular"):
        export(root, trial, tmp_path / "export")


def test_record_count_is_bounded_by_schedule_attempts(linked, tmp_path):
    root, document, trial, _ = linked
    for number in range(len(document["trials"]) * 100 + 1):
        (root / "records" / f"slot-001-attempt-{number:03d}.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="record bound"):
        export(root, trial, tmp_path / "export")
