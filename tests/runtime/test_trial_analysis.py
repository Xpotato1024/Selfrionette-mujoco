"""保存済み試行を実行せずに検査し、条件の欠落を解析成功としない。"""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from xpotato_sim.runtime.experiment.continuous_record import comparison_metrics
from xpotato_sim.runtime.experiment.trial_analysis import analyze_trial, load_validated_trial
from xpotato_sim.runtime.scene.objects import canonical
from tests.runtime.test_research_spring_demo import prepared, run


@pytest.fixture(scope="module")
def recorded_trial(tmp_path_factory):
    root = tmp_path_factory.mktemp("trial-analysis-base")
    runner, ticket, clock = prepared(root)
    try:
        run(runner, ticket, clock)
    finally:
        runner.close()
    return root / ticket.trial_id


@pytest.fixture
def trial(recorded_trial, tmp_path):
    return Path(shutil.copytree(recorded_trial, tmp_path / recorded_trial.name))


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    path.write_bytes(canonical(value))


def rewrite_rows(root, change):
    path = root / "samples.jsonl"
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    change(rows)
    data = b"".join(canonical(row) + b"\n" for row in rows)
    path.write_bytes(data)
    terminal = read_json(root / "terminal.json")
    terminal["continuous_ref"].update(sha256=sha256(data).hexdigest(), bytes=len(data))
    write_json(root / "terminal.json", terminal)


@pytest.mark.parametrize("name", ["condition.json", "start.json", "initial-state.json", "final-state.json"])
def test_missing_referenced_artifact_is_not_analyzable(trial, name):
    (trial / name).unlink()
    with pytest.raises(ValueError, match="artifact"):
        comparison_metrics(trial)


def test_terminal_row_is_required_even_with_matching_file_hash(trial):
    rewrite_rows(trial, lambda rows: rows.pop())
    with pytest.raises(ValueError, match="terminal"):
        comparison_metrics(trial)


def test_changed_condition_is_not_analyzable(trial):
    path = trial / "condition.json"
    document = read_json(path)
    document["condition"]["dt_s"] = .5
    write_json(path, document)
    with pytest.raises(ValueError, match="digest"):
        comparison_metrics(trial)


def rewrite_terminal(root, change):
    path = root / "terminal.json"
    document = read_json(path)
    change(document)
    write_json(path, document)


def test_analysis_preserves_conditions_provenance_and_terminal_classification(trial):
    analysis = analyze_trial(trial)
    saved = read_json(trial / "condition.json")
    start = read_json(trial / "start.json")
    terminal = read_json(trial / "terminal.json")
    assert analysis["condition"] == saved["condition"]
    assert analysis["input_provenance"] == start["input_provenance"]
    assert analysis["runner_stop_reason"] == "simulation_budget"
    assert analysis["task_outcome"] == terminal["task_outcome"]
    assert analysis["task_outcome"]["classification"] == "failure"
    assert analysis["metrics"]["ticks"] == 4
    assert analysis["metrics"]["input_samples"] == 2
    assert analysis["metrics"]["peak_contact_force_n"] is None
    assert analysis["metrics"]["target_contacts"][0]["peak_resultant_force_n"] is None
    assert analysis["simulation_time_s"] == terminal["simulation_time_s"]
    assert analysis["terminal_sha256"] == sha256((trial / "terminal.json").read_bytes()).hexdigest()


def test_validated_snapshot_does_not_reopen_modified_files(trial):
    snapshot = load_validated_trial(trial)
    (trial / "samples.jsonl").write_bytes(b"corrupted after validation")
    rows = list(snapshot.iter_rows(kind="tick"))
    assert len(rows) == 4
    rows[0]["qpos"][0] = 999.
    assert next(snapshot.iter_rows(kind="tick"))["qpos"][0] != 999.
    analysis = snapshot.analysis()
    analysis["metrics"]["ticks"] = 999
    assert snapshot.analysis()["metrics"]["ticks"] == 4
    with pytest.raises(ValueError, match="digest"):
        analyze_trial(trial)


@pytest.mark.parametrize("change,match", [
    (lambda t: t.update(recording="failed"), "completed"),
    (lambda t: t.update(schema_version="trial-terminal/v99"), "schema"),
    (lambda t: t.update(ticks=True), "integer"),
    (lambda t: t.update(runner_stop_reason="invented_success"), "reason"),
    (lambda t: t.update(runner_stop_reason="task_success"), "classification"),
    (lambda t: t["start_ref"].update(file="../start.json"), "reference"),
    (lambda t: t.update(input_accepting_monotonic_s=1e8), "timestamp"),
    (lambda t: t.update(simulation_time_s=10.), "timestamp"),
    (lambda t: t.update(software_revision="other-source"), "identity"),
])
def test_terminal_contract_is_checked(trial, change, match):
    rewrite_terminal(trial, change)
    with pytest.raises(ValueError, match=match):
        analyze_trial(trial)


@pytest.mark.parametrize("change,match", [
    (lambda rows: rows[0].update(schema_version="trial-continuous/v99"), "schema"),
    (lambda rows: rows[0].update(software_revision="other-source"), "identity"),
    (lambda rows: rows[-1].update(runner_stop_reason="task_failure"), "terminal"),
    (lambda rows: rows.append(rows[0]), "after terminal"),
    (lambda rows: rows[0].update(received_at_s=0.), "timestamp"),
    (lambda rows: rows[2].update(simulation_time_s=2.), "timestamp"),
    (lambda rows: rows[2]["qpos"].__setitem__(0, True), "number"),
    (lambda rows: rows[2]["dynamics"]["springs"][0].update(restoring_force_n=True), "number"),
    (lambda rows: rows[2]["dynamics"].update(model_sha256="0"*64), "identity"),
    (lambda rows: rows[2]["dynamics"].update(springs=[]), "spring"),
])
def test_rehashed_rows_still_require_valid_contract(trial, change, match):
    rewrite_rows(trial, change)
    with pytest.raises(ValueError, match=match):
        analyze_trial(trial)


def test_last_state_must_match_committed_tick(trial):
    path = trial / "final-state.json"
    final = read_json(path)
    final["qpos"][0] += 1.
    write_json(path, final)
    rewrite_terminal(trial, lambda t: t["final_state_ref"].update(sha256=sha256(path.read_bytes()).hexdigest()))
    with pytest.raises(ValueError, match="last committed tick"):
        analyze_trial(trial)


def test_rehashing_condition_file_does_not_hide_changed_semantic_digest(trial):
    path = trial / "condition.json"
    document = read_json(path)
    document["condition"]["dt_s"] = .5
    write_json(path, document)
    start_path = trial / "start.json"
    start = read_json(start_path)
    start["condition_ref"]["sha256"] = sha256(path.read_bytes()).hexdigest()
    write_json(start_path, start)
    rewrite_terminal(trial, lambda t: t["start_ref"].update(sha256=sha256(start_path.read_bytes()).hexdigest()))
    with pytest.raises(ValueError, match="semantic digest"):
        analyze_trial(trial)


def test_file_and_line_bounds_precede_parsing(trial, monkeypatch):
    monkeypatch.setattr("xpotato_sim.runtime.experiment.trial_analysis.MAX_CONTINUOUS_BYTES", 1)
    with pytest.raises(ValueError, match="bounded regular artifact"):
        analyze_trial(trial)


def test_nonfinite_and_duplicate_json_values_are_rejected(trial):
    path = trial / "terminal.json"
    original = path.read_bytes()
    for addition in (b'"bad":NaN,', b'"ticks":4,'):
        path.write_bytes(b"{" + addition + original[1:])
        with pytest.raises(ValueError, match="nonfinite|duplicate"):
            analyze_trial(trial)


@pytest.mark.parametrize("reason", ["technical_invalid", "operator_abort", "input_wait_timeout", "wall_timeout"])
def test_non_success_recorded_trials_remain_analyzable(tmp_path, reason):
    runner, ticket, clock = prepared(tmp_path)
    try:
        runner.start(ticket, input_provenance={"source": "explicit-software-fixture"})
        if reason == "technical_invalid":
            runner.fail(ticket, "explicit fixture fault")
        elif reason == "operator_abort":
            runner.abort(ticket)
        else:
            clock.sleep(361 if reason == "wall_timeout" else 6)
            runner.advance(ticket)
        result = analyze_trial(tmp_path / ticket.trial_id)
        assert result["runner_stop_reason"] == reason
        assert result["metrics"]["ticks"] == 0
        assert result["metrics"]["peak_contact_force_n"] is None
        assert result["metrics"]["site_path_length_between_recorded_ticks_m"] == {}
    finally:
        runner.close()


def test_target_resultant_ignores_support_contacts_and_sums_same_pair(trial):
    def contacts(rows):
        tick = next(row for row in rows if row["kind"] == "tick")
        tool = {"kind": "tool", "id": "arm"}
        obj = {"kind": "object", "id": "cube"}
        tick["dynamics"]["contacts"] = [
            {"role1": {"kind":"support", "id":"floor"}, "role2": obj,
             "status":"measured", "force_on_geom2_world_n":[100.,0.,0.]},
            {"role1": obj, "role2": tool, "status":"measured", "force_on_geom2_world_n":[3.,0.,0.]},
            {"role1": tool, "role2": obj, "status":"measured", "force_on_geom2_world_n":[0.,-4.,0.]},
        ]
    rewrite_rows(trial, contacts)
    metrics = analyze_trial(trial)["metrics"]
    assert metrics["peak_contact_force_n"] == 100.
    pair = metrics["target_contacts"][0]
    assert pair["peak_resultant_force_n"] == 5.
    assert pair["peak_contact_point_force_n"] == 4.
    assert pair["samples_with_contact"] == 1
    assert pair["unavailable_contact_points"] == 0


def test_partial_contact_does_not_report_partial_sum_as_resultant(trial):
    def contacts(rows):
        tick = next(row for row in rows if row["kind"] == "tick")
        pair = {"role1":{"kind":"object", "id":"cube"}, "role2":{"kind":"tool", "id":"arm"}}
        tick["dynamics"]["contacts"] = [
            {**pair, "status":"measured", "force_on_geom2_world_n":[3.,0.,0.]},
            {**pair, "status":"measurement_unavailable", "force_on_geom2_world_n":None},
        ]
    rewrite_rows(trial, contacts)
    metrics = analyze_trial(trial)["metrics"]
    assert metrics["peak_contact_force_n"] == 3.
    assert metrics["missing_measurements"] == 1
    assert metrics["target_contacts"][0]["peak_resultant_force_n"] is None


def test_tick_entry_timestamp_may_precede_input_callback_timestamp(trial):
    def times(rows):
        inputs = [row for row in rows if row["kind"] == "input"]
        inputs[-1]["host_monotonic_s"] += .005
        rows[-1]["host_monotonic_s"] += .01
    rewrite_rows(trial, times)
    rewrite_terminal(trial, lambda t: t.update(terminal_monotonic_s=t["terminal_monotonic_s"] + .01))
    assert analyze_trial(trial)["metrics"]["ticks"] == 4


def test_partial_marker_is_not_a_completed_trial(trial):
    (trial / "terminal.json").rename(trial / "terminal.json.pending")
    with pytest.raises(ValueError, match="artifact unavailable"):
        analyze_trial(trial)


def test_optional_signals_preserve_values_without_changing_raw_metrics(trial):
    expected = analyze_trial(trial)["metrics"]
    def signals(rows):
        for row in rows:
            if row["kind"] == "tick":
                row["signals"] = {"scene_force_signal_v1": {"schema_version":"scene-force-signal/v1", "status":"fixture-only"}}
    rewrite_rows(trial, signals)
    snapshot = load_validated_trial(trial)
    assert snapshot.analysis()["metrics"] == expected
    assert next(snapshot.iter_rows(kind="tick"))["signals"]["scene_force_signal_v1"]["status"] == "fixture-only"
    rewrite_rows(trial, lambda rows: next(row for row in rows if row["kind"] == "tick").update(signals=[]))
    with pytest.raises(ValueError, match="signals"):
        analyze_trial(trial)


def test_technical_invalid_with_unavailable_final_state_is_retained(tmp_path, monkeypatch):
    runner, ticket, clock = prepared(tmp_path)
    try:
        runner.start(ticket, input_provenance={"source": "explicit-software-fixture"})
        def failed_state():
            raise RuntimeError("fixture final state unavailable")
        monkeypatch.setattr(runner._execution.instance.provider, "trial_state", failed_state)
        runner.fail(ticket, "explicit fixture fault")
        analysis = analyze_trial(tmp_path / ticket.trial_id)
        assert analysis["runner_stop_reason"] == "technical_invalid"
        assert "final state unavailable" in analysis["error"]
    finally:
        runner.close()
