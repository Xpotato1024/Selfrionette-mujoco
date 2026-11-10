"""実MuJoCoの保存trialから失敗も含めて再解析し、条件未定義の誤差を捏造しない。"""
import csv
import json
from pathlib import Path

import pytest

from tests.runtime.test_research_spring_demo import prepared, run
from tests.runtime.test_trial_runner import start
from xpotato_sim.runtime.experiment.pilot_export import export_results
from xpotato_sim.runtime.experiment.trial_analysis import load_validated_trial


def make_result(root, *, abort=False):
    runner, ticket, clock = prepared(root)
    try:
        if abort:
            start(runner, ticket, clock)
            runner.abort(ticket)
        else:
            run(runner, ticket, clock)
    finally:
        runner.close()
    return root / ticket.trial_id


def test_export_keeps_abort_incomplete_and_does_not_invent_target(tmp_path):
    root = tmp_path / "results"
    make_result(root)
    make_result(root, abort=True)
    incomplete = root / "incomplete"
    incomplete.mkdir()
    (incomplete / "samples.jsonl.pending").write_bytes(b"unfinished")
    output = tmp_path / "export"
    report = export_results(result_root=root, output=output, plots=False)
    assert report["trial_count"] == 3
    assert report["verified_count"] == 2
    assert report["invalid_or_incomplete_count"] == 1
    assert report["stop_reasons"] == {"simulation_budget": 1, "operator_abort": 1}
    assert report["participant_count"] == 0
    assert all(trial["force_error"] is None for trial in report["trials"])
    assert json.loads((output / "analysis.json").read_bytes()) == report
    with (output / "trials.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3
    assert sum(row["integrity"] == "invalid_or_incomplete" for row in rows) == 1
    assert any(row.get("runner_stop_reason") == "operator_abort" for row in rows)
    assert all(not row.get("mae_n") for row in rows)


def test_explicit_spring_force_target_and_native_time_rounding(tmp_path):
    directory = make_result(tmp_path / "results")
    report = export_results(result_root=directory, output=tmp_path / "analysis",
        spring_object="cube", target_force_n=1., window_start_s=.05, window_end_s=4/60, plots=True)
    trial = report["trials"][0]
    error = trial["force_error"]
    row = next(row for row in load_validated_trial(directory).iter_rows(kind="tick") if row["tick"] == 3)
    spring_load = -row["dynamics"]["springs"][0]["restoring_force_n"]
    assert error["status"] == "computed" and error["sample_count"] == 1
    assert error["mae_n"] == pytest.approx(abs(spring_load - 1.))
    assert error["bias_n"] == pytest.approx(spring_load - 1.)
    assert error["specification"]["quantity"] == "spring_restoring_load_n"
    images = list((tmp_path / "analysis" / "figures").glob("*.png"))
    assert len(images) == 1 and images[0].read_bytes().startswith(b"\x89PNG")


def test_partial_interval_is_unavailable_not_zero(tmp_path):
    directory = make_result(tmp_path / "results")
    report = export_results(result_root=directory, output=tmp_path / "analysis",
        spring_object="cube", target_force_n=1., window_start_s=0., window_end_s=1., plots=False)
    error = report["trials"][0]["force_error"]
    assert error["status"] == "unavailable" and error["mae_n"] is None
    assert error["reason"] == "trial_ended_before_analysis_interval"


@pytest.mark.parametrize("kwargs", [
    {"target_force_n": 1.},
    {"spring_object": "cube", "target_force_n": float("nan"), "window_start_s": 0., "window_end_s": 1.},
    {"spring_object": "cube", "target_force_n": -1., "window_start_s": 0., "window_end_s": 1.},
    {"spring_object": "cube", "target_force_n": 1., "window_start_s": 1., "window_end_s": 1.},
])
def test_undefined_target_rejected_before_output(tmp_path, kwargs):
    directory = make_result(tmp_path / "results")
    with pytest.raises(ValueError):
        export_results(result_root=directory, output=tmp_path / "analysis", plots=False, **kwargs)
    assert not (tmp_path / "analysis").exists()


def test_output_failure_does_not_publish_completed_report(tmp_path, monkeypatch):
    directory = make_result(tmp_path / "results")
    def fail(*args, **kwargs):
        raise OSError("disk failure")
    monkeypatch.setattr("xpotato_sim.runtime.experiment.pilot_export._plot_series", fail)
    with pytest.raises(OSError, match="disk failure"):
        export_results(result_root=directory, output=tmp_path / "analysis")
    assert not (tmp_path / "analysis" / "analysis.json").exists()


def test_final_report_flush_failure_does_not_publish_completed_report(tmp_path, monkeypatch):
    directory = make_result(tmp_path / "results")
    def fail(*args, **kwargs):
        raise OSError("final report disk failure")
    monkeypatch.setattr("xpotato_sim.runtime.experiment.pilot_export.os.fsync", fail)
    with pytest.raises(OSError, match="final report disk failure"):
        export_results(result_root=directory, output=tmp_path / "analysis", plots=False)
    assert (tmp_path / "analysis" / "analysis.json.pending").exists()
    assert not (tmp_path / "analysis" / "analysis.json").exists()


def test_export_does_not_overwrite_and_duplicate_trial_is_not_extra_participant(tmp_path):
    import shutil
    directory = make_result(tmp_path / "results")
    shutil.copytree(directory, directory.parent / "duplicate")
    output = tmp_path / "analysis"
    report = export_results(result_root=directory.parent, output=output, plots=False)
    assert report["verified_count"] == 1 and report["invalid_or_incomplete_count"] == 1
    assert report["participant_count"] == 0
    before = (output / "analysis.json").read_bytes()
    with pytest.raises(FileExistsError):
        export_results(result_root=directory.parent, output=output, plots=False)
    assert (output / "analysis.json").read_bytes() == before


def test_cli_reports_integrity_failure_with_nonzero_exit(tmp_path, capsys):
    from xpotato_sim.cli.main import main
    root = tmp_path / "results"
    make_result(root)
    (root / "incomplete").mkdir()
    assert main(["experiment", "analyze", "--result-root", str(root),
                 "--output", str(tmp_path / "analysis"), "--no-plots"]) == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["verified_count"] == 1 and printed["invalid_or_incomplete_count"] == 1


def test_session_exports_missing_slots_and_unlinked_trials_without_counting_fixture_as_person(tmp_path):
    from tests.runtime.test_pilot_session import arguments, read, record
    from xpotato_sim.runtime.experiment.pilot_session import attach_trial, create_session
    root = tmp_path / "session"
    create_session(**arguments(root))
    session = root / "session.json"
    linked = record(tmp_path / "results", read(root / "g_off.json"))
    unlinked = record(tmp_path / "results", read(root / "g_on.json"))
    attach_trial(session_path=session, slot=1, trial_directory=linked)
    report = export_results(result_root=tmp_path / "results", output=tmp_path / "analysis", session_path=session, plots=False)
    assert report["verified_count"] == 2
    assert report["participant_count"] == 0 and report["software_fixture_id_count"] == 1
    assert report["missing_linked_trial_ids"] == []
    assert report["unlinked_trial_ids"] == [unlinked.name]
    assert report["unattempted_slots"] == [2, 3, 4]
    assert report["session_linkage_complete"] is False


def test_cli_returns_incomplete_for_unattempted_session_even_when_all_files_verify(tmp_path, capsys):
    from tests.runtime.test_pilot_session import arguments, read, record
    from xpotato_sim.runtime.experiment.pilot_session import attach_trial, create_session
    from xpotato_sim.cli.main import main
    root = tmp_path / "session"
    create_session(**arguments(root))
    trial = record(tmp_path / "results", read(root / "g_off.json"))
    attach_trial(session_path=root / "session.json", slot=1, trial_directory=trial)
    assert main(["experiment", "analyze", "--result-root", str(trial.parent),
        "--session", str(root / "session.json"), "--output", str(tmp_path / "analysis"), "--no-plots"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["invalid_or_incomplete_count"] == 0
    assert report["unattempted_slots"] == [2, 3, 4]
    assert report["session_linkage_complete"] is False
