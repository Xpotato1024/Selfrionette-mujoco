"""raw動画用の時刻・姿勢・条件一致を、実MuJoCo記録で検査する。"""
from pathlib import Path
from types import SimpleNamespace
import json
import mujoco
import pytest
from xpotato_sim.runtime.experiment import video_bundle
from xpotato_sim.runtime.experiment.edited_condition import preset_condition, resolve_condition
from xpotato_sim.runtime.experiment.trial_runner import TrialRunner
from xpotato_sim.runtime.experiment.trial_analysis import load_validated_trial
from tests.runtime.test_trial_runner import Clock, start, message


def saved_trial(root, name):
    doc = preset_condition(name, input_provider="gamepad/v1")
    doc["limits"]["max_ticks"] = 4
    profile, limits, _ = resolve_condition(doc)
    clock = Clock()
    runner = TrialRunner(result_root=root, software_revision="video-test-only", clock=clock)
    ticket = runner.prepare(profile, limits)
    start(runner, ticket, clock)
    for i in range(1, 5):
        clock.sleep(profile.dt_s)
        runner.ingest(ticket, message(i), received_at_s=clock())
        runner.advance(ticket)
    runner.close()
    return root / ticket.trial_id


def test_time_sampling_is_causal_without_interpolation():
    assert video_bundle.frame_schedule([10., 10.01, 10.05, 10.1], 30) == [0, 1, 2]
    assert len(video_bundle.frame_schedule([0., 13.0000000000012], 30)) == 390
    assert video_bundle.frame_schedule([0., .1], 60) == [0]*6


@pytest.mark.parametrize("times,fps", [([0., 0.], 30), ([0., -1.], 30), ([0., float("nan")], 30),
    ([0.], 30), ([0., 1.], 0), ([0., 1.], True), ([0., 100000.], 120)])
def test_invalid_timeline_rejected(times, fps):
    with pytest.raises(ValueError):
        video_bundle.frame_schedule(times, fps)


@pytest.mark.parametrize("name", ["tasks/research-spring", "tasks/research-spring-plate", "tasks/dynamic-cube-drop"])
def test_bundle_is_task_independent_and_never_integrates(tmp_path, monkeypatch, name):
    directory = saved_trial(tmp_path / "trials", name)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    def forbidden(*args, **kwargs):
        raise AssertionError("physics integration during video export")
    monkeypatch.setattr(mujoco, "mj_step", forbidden)
    frames, evidence = video_bundle.build_video_bundle(directory, tmp_path / "video")
    assert len(frames) == 5
    assert evidence["max_site_reconstruction_error_m"] < 1e-10
    assert evidence["physics_stepped_during_export"] is False
    rows = list(load_validated_trial(directory).iter_rows(kind="tick"))
    assert [frame["qpos"] for frame in frames[1:]] == [row["qpos"] for row in rows]
    bundle = json.loads((tmp_path / "video/public/replay.json").read_text())
    assert bundle["initial"]["metadata"]["source_active"] is False
    assert bundle["camera"] == "operator"
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    with pytest.raises(FileExistsError):
        video_bundle.build_video_bundle(directory, tmp_path / "video")
    with pytest.raises(ValueError, match="trial directory"):
        video_bundle.build_video_bundle(directory, directory / "video")


def test_corrupt_log_does_not_become_video(tmp_path):
    directory = saved_trial(tmp_path / "trials", "tasks/research-spring-plate")
    with (directory / "samples.jsonl").open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="digest"):
        video_bundle.build_video_bundle(directory, tmp_path / "video")
    assert not (tmp_path / "video").exists()


def test_other_model_revision_rejected(tmp_path, monkeypatch):
    directory = saved_trial(tmp_path / "trials", "tasks/research-spring-plate")
    fake = SimpleNamespace(viewer=SimpleNamespace(metadata={"model_sha256": "0"*64}))
    monkeypatch.setattr(video_bundle, "decode_launch_profile", lambda *a, **k: SimpleNamespace(build_model=lambda: fake))
    with pytest.raises(ValueError, match="model differs"):
        video_bundle.build_video_bundle(directory, tmp_path / "video")


def test_plate_has_real_collision_thickness_and_preserves_front_surface():
    old = preset_condition("tasks/research-spring", input_provider="gamepad/v1")
    new = preset_condition("tasks/research-spring-plate", input_provider="gamepad/v1")
    a = resolve_condition(old)[0].build_model()
    b = resolve_condition(new)[0].build_model()
    assert a.viewer.metadata["model_sha256"] != b.viewer.metadata["model_sha256"]
    model = b.provider.model
    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "object__plate")
    geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == body]
    assert len(geoms) == 1
    geom = geoms[0]
    assert model.geom_size[geom].tolist() == [.05, .005, .05]
    assert model.body_mass[body] == pytest.approx(.1)
    assert model.geom_rgba[geom][3] == 1
    assert model.body_pos[body][1] + model.geom_size[geom][1] == pytest.approx(-.31)
    assert model.body_inertia[body][0] == pytest.approx(.1/3*(.005**2+.05**2))
    assert new["task"]["parameters"]["target_object_ids"] == ["plate"]
