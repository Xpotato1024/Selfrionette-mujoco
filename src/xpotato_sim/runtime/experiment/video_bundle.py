"""検証済み有限試行の姿勢をraw動画へ渡す。Task・入力・力の再計算は行わない。"""
from __future__ import annotations
from bisect import bisect_right
from copy import deepcopy
from hashlib import sha256
import json
from math import ceil, isfinite
from pathlib import Path
from .trial_analysis import load_validated_trial
from xpotato_sim.runtime.composition.launch_profile import decode_launch_profile, repository_workspace
from xpotato_sim.runtime.scene.objects import canonical

CAMERAS = ("operator", "iso", "front", "side", "top")


def frame_schedule(times, fps):
    """記録開始から等速。各表示時刻以前の最新状態を採用し、補間で姿勢を作らない。"""
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("fps must be an integer in [1, 120]")
    if len(times) < 2 or any(type(t) not in (int, float) or not isfinite(t) for t in times):
        raise ValueError("at least two finite simulation timestamps required")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("strictly increasing simulation timestamps required")
    duration = times[-1] - times[0]
    count = ceil(duration * fps - 1e-8)
    if not 1 <= count <= 100000:
        raise ValueError("video frame budget exceeded")
    return [max(0, bisect_right(times, times[0] + i / fps + 1e-9) - 1) for i in range(count)]


def _read_referenced(directory, name, expected):
    path = directory / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("bounded regular trial artifact required")
    value = path.read_bytes()
    if sha256(value).hexdigest() != expected:
        raise ValueError("artifact changed after validation: " + name)
    return json.loads(value)


def build_video_bundle(directory: Path, destination: Path, *, camera="operator"):
    """modelのdigestが一致した状態だけ出力する。異版や欠測へ代替姿勢を補わない。"""
    if camera not in CAMERAS:
        raise ValueError("unknown camera preset")
    directory, destination = Path(directory).resolve(), Path(destination).resolve()
    if destination == directory or directory in destination.parents:
        raise ValueError("video output must not modify trial directory")
    if destination.exists():
        raise FileExistsError(destination)
    trial = load_validated_trial(directory)
    analysis = trial.analysis()
    terminal = _read_referenced(directory, "terminal.json", analysis["terminal_sha256"])
    start = _read_referenced(directory, "start.json", terminal["start_ref"]["sha256"])
    initial = _read_referenced(directory, "initial-state.json", start["initial_state_ref"]["sha256"])
    config = deepcopy(analysis["origin_profile"]["configuration"])
    workspace = repository_workspace()
    # 保存条件の物理値は保持。resource探索先だけ現在のcheckoutへ解決する。
    config["workspace"] = str(workspace)
    profile = decode_launch_profile(canonical(config), source_path=workspace / "profiles" / "recorded-video.json")
    instance = profile.build_model()
    if instance.viewer.metadata["model_sha256"] != analysis["condition"]["model_sha256"]:
        raise ValueError("recorded model differs from current model; use the recorded revision")
    model = getattr(instance.provider, "model", None)
    if model is None or model.nmocap:
        raise ValueError("raw video requires a native model with all moving poses recorded in qpos")
    import mujoco
    import numpy as np
    data = mujoco.MjData(model)
    frames = [{"tick": 0, "time_s": initial["time_s"], "qpos": initial["qpos"], "qvel": initial["qvel"]}]
    max_site_error = 0.0
    for row in trial.iter_rows(kind="tick"):
        if len(row["qpos"]) != model.nq or len(row["qvel"]) != model.nv:
            raise ValueError("recorded state dimensions differ from model")
        data.qpos[:] = row["qpos"]
        data.qvel[:] = row["qvel"]
        data.time = row["simulation_time_s"]
        mujoco.mj_kinematics(model, data)
        for site in row["sites"]:
            sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site["name"])
            if sid < 0:
                raise ValueError("recorded site absent from model")
            error = float(np.linalg.norm(data.site_xpos[sid] - site["position_m"]))
            max_site_error = max(max_site_error, error)
        frames.append({"tick": row["tick"], "time_s": row["simulation_time_s"],
                       "qpos": row["qpos"], "qvel": row["qvel"]})
    if len(frames) < 2 or max_site_error > 1e-8:
        raise ValueError("no committed poses or recorded/native site mismatch")
    epoch = analysis["epoch"]
    metadata = {**dict(instance.viewer.metadata), "physical_output": "disabled", "source_active": False,
        "coordinated_runtime_v1": {"schema_version": "coordinated-runtime-presentation/v1",
            "epoch": epoch, "state": "stopped", "reason": "offline recorded poses", "tick": 0,
            "arm_ids": list(instance.provider.endpoint_ids)}}
    payload = {"version": 0, "frame_index": 0, "time_s": initial["time_s"],
               "qpos": initial["qpos"], "qvel": initial["qvel"], "bodies": [], "sites": [],
               "target_position_m": None, "metadata": metadata}
    destination.mkdir(parents=True)
    public = destination / "public"
    # Windowsの深い一時directoryでも、hash付きasset pathを途中で欠落させない。
    import os
    if os.name == "nt":
        value = str(public)
        prefix = chr(92)*2 + "?" + chr(92)
        public = Path(prefix + ("UNC" + chr(92) + value[2:] if value.startswith(chr(92)*2) else value))
    instance.viewer.write_public_tree(public)
    bundle = {"schema": "raw-video-bundle/v1", "camera": camera, "epoch": epoch,
              "initial": payload, "frames": frames}
    (destination / "public" / "replay.json").write_bytes(canonical(bundle))
    evidence = {"schema": "raw-video-evidence/v1", "trial_id": analysis["trial_id"],
        "simulation_revision": analysis["software_revision"], "model_sha256": metadata["model_sha256"],
        "terminal_sha256": analysis["terminal_sha256"], "input_provenance": analysis["input_provenance"],
        "runner_stop_reason": analysis["runner_stop_reason"], "task_outcome": analysis["task_outcome"],
        "camera": camera, "recorded_ticks": len(frames)-1,
        "simulation_time_s": frames[-1]["time_s"]-frames[0]["time_s"],
        "max_site_reconstruction_error_m": max_site_error,
        "interpolation": "none; latest recorded pose at or before frame timestamp",
        "overlays": False, "physics_stepped_during_export": False}
    return frames, evidence
