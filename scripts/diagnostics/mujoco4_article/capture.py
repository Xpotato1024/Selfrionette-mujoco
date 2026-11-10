"""隔離した MuJoCo 4.0.0 で記事用の実シミュレーション素材を生成する。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
UPSTREAM = "ac60eae30fa7e0d31315c38d9476752fb81be67e"
SCENES = ("torsion", "foil")
FPS = 20
RATE = 0.3
SECONDS = 6
WIDTH, HEIGHT = 800, 500


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def model_xml(name: str) -> tuple[str, dict]:
    """原本を改変せず、比較の交絡を減らした入力を別に作る。"""
    if name not in SCENES:
        raise ValueError(f"unknown scene: {name}")
    source = HERE / "models" / f"{name}.xml"
    provenance = json.loads((HERE / "models" / "provenance.json").read_text(encoding="utf-8"))
    if sha256(source) != provenance["files"][source.name]:
        raise ValueError("upstream model hash mismatch")
    tree = ET.fromstring(source.read_text(encoding="utf-8"))
    option = tree.find("option")
    assert option is not None
    option.set("solver", "CG")
    damping = "0.025" if name == "torsion" else "0.010"
    for elasticity in tree.findall(".//elasticity"):
        elasticity.set("damping", damping)
    changes = {"solver": "CG", "both_elasticity_damping": damping}
    return ET.tostring(tree, encoding="unicode"), changes


def require_version() -> None:
    if mujoco.__version__ != "4.0.0":
        raise RuntimeError("Use the isolated environment with mujoco==4.0.0; do not upgrade the Sim runtime.")


def check_state(data: mujoco.MjData) -> None:
    if not all(np.isfinite(x).all() for x in (data.qpos, data.qvel, data.plastic)):
        raise RuntimeError("non-finite simulation state")
    if np.any(data.warning.number):
        raise RuntimeError(f"MuJoCo warnings: {data.warning.number.tolist()}")


def advance(model: mujoco.MjModel, data: mujoco.MjData, target: float) -> None:
    steps = max(0, math.ceil((target - float(data.time) - 1e-10) / model.opt.timestep))
    if steps:
        mujoco.mj_step(model, data, nstep=steps)
    check_state(data)
    mujoco.mj_forward(model, data)


def measure(model: mujoco.MjModel, data: mujoco.MjData, initial: np.ndarray) -> dict:
    result = {"time_s": float(data.time), "warnings": data.warning.number.tolist()}
    if model.nflex:
        result["flex_rms_displacement_m"] = [
            float(np.sqrt(np.mean(np.sum((data.flexvert_xpos[a:a+n] - initial[a:a+n]) ** 2, axis=1))))
            for a, n in zip(model.flex_vertadr, model.flex_vertnum)
        ]
    result["plastic_state_sha256"] = hashlib.sha256(data.plastic.tobytes()).hexdigest()
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "twist_0") >= 0:
        result["cap_twist_deg"] = [math.degrees(float(data.joint(f"twist_{i}").qpos[0])) for i in range(2)]
    return result


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default(size=size)


def label_frame(pixels: np.ndarray) -> Image.Image:
    frame = Image.new("RGB", (WIDTH, HEIGHT), (20, 30, 42))
    frame.paste(Image.fromarray(pixels), (0, 50))
    draw = ImageDraw.Draw(frame)
    draw.text((WIDTH * .25, 25), "Elastic", anchor="mm", font=font(32), fill="white")
    draw.text((WIDTH * .75, 25), "Elasto-plastic", anchor="mm", font=font(32), fill="white")
    return frame


def encode(directory: Path, ffmpeg: str) -> dict:
    """同一PNG列から各形式を作り、デコード可能性と容量を保存する。"""
    common = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-framerate", str(FPS),
              "-i", str(directory / "frames" / "%04d.png")]
    formats = {
        "gif": ["-filter_complex", "split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3", "-loop", "0"],
        "mp4": ["-an", "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        "webm": ["-an", "-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-pix_fmt", "yuv420p"],
    }
    manifest = {}
    for extension, options in formats.items():
        destination = directory / f"animation.{extension}"
        subprocess.run(common + options + [str(destination)], check=True, timeout=180)
        subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(destination), "-f", "null", "-"], check=True, timeout=60)
        manifest[extension] = {"bytes": destination.stat().st_size, "sha256": sha256(destination), "options": options}
    with Image.open(directory / "animation.gif") as image:
        count = image.n_frames
        durations = []
        for i in range(count):
            image.seek(i)
            durations.append(image.info.get("duration", 0))
        if sum(durations) != SECONDS * 1000:
            raise RuntimeError(f"unexpected GIF duration: {sum(durations)} ms")
        manifest["gif"].update(frame_count=count, duration_ms=sum(durations), size=list(image.size))
    return manifest


def capture(name: str, output: Path, ffmpeg: str) -> dict:
    directory = output / name
    directory.mkdir()
    frames = directory / "frames"
    frames.mkdir()
    xml, changes = model_xml(name)
    (directory / "model.xml").write_text(xml, encoding="utf-8")
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    initial = data.flexvert_xpos.copy()
    model.vis.global_.offwidth = WIDTH
    model.vis.global_.offheight = HEIGHT - 50
    model.vis.quality.shadowsize = 4096
    camera = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(model, camera)
    camera.azimuth, camera.elevation = 90, -25
    camera.distance = .95 if name == "torsion" else 1.1
    camera.lookat[:] = model.stat.center
    states, qpos, qvel, plastic = [], [], [], []
    started = time.perf_counter()
    with mujoco.Renderer(model, height=HEIGHT - 50, width=WIDTH) as renderer:
        for index in range(FPS * SECONDS):
            advance(model, data, index * RATE / FPS)
            states.append({"frame": index, "playback_time_s": index / FPS, **measure(model, data, initial)})
            qpos.append(data.qpos.copy()); qvel.append(data.qvel.copy()); plastic.append(data.plastic.copy())
            renderer.update_scene(data, camera=camera)
            image = label_frame(renderer.render())
            image.save(frames / f"{index:04d}.png")
            if index == 0:
                image.save(directory / "initial.png")
            if index == FPS * SECONDS - 1:
                image.save(directory / "poster.png")
                image.save(directory / "poster.webp", quality=86, method=6)
        advance(model, data, 4.8)
        final = measure(model, data, initial)
    capture_seconds = time.perf_counter() - started
    np.savez_compressed(directory / "states.npz", qpos=np.asarray(qpos), qvel=np.asarray(qvel), plastic=np.asarray(plastic))
    write_json(directory / "frame-times.json", states)
    with (directory / "measurements.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "playback_time_s", "simulation_time_s", "elastic_rms_m", "plastic_rms_m", "elastic_cap_deg", "plastic_cap_deg"])
        for row in states:
            writer.writerow([row["frame"], row["playback_time_s"], row["time_s"], *row["flex_rms_displacement_m"], *row.get("cap_twist_deg", ["", ""])])
    report = {"scene": name, "engine": mujoco.__version__, "renderer": "MuJoCo native OpenGL (not Filament, not Xpotato-Sim Web Viewer)",
              "upstream_commit": UPSTREAM, "upstream_model_sha256": sha256(HERE / "models" / f"{name}.xml"),
              "adapted_model_sha256": sha256(directory / "model.xml"), "changes": changes,
              "nv": model.nv, "timestep_s": model.opt.timestep, "camera": {"azimuth": camera.azimuth, "elevation": camera.elevation, "distance": camera.distance, "lookat": camera.lookat.tolist()},
              "fps": FPS, "playback_rate": RATE, "playback_seconds": SECONDS,
              "frame_count": FPS * SECONDS, "last_frame_simulation_s": states[-1]["time_s"],
              "final_measurement": final, "capture_wall_seconds_including_render_and_io": capture_seconds,
              "states_sha256": sha256(directory / "states.npz"), "frames_sha256": [sha256(p) for p in sorted(frames.glob("*.png"))],
              "encodings": encode(directory, ffmpeg)}
    write_json(directory / "manifest.json", report)
    print(json.dumps({k: report[k] for k in ("scene", "nv", "final_measurement", "encodings")}), flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    args = parser.parse_args()
    require_version()
    ffmpeg = shutil.which(args.ffmpeg)
    if not ffmpeg:
        parser.error("ffmpeg is required")
    output = args.output.resolve()
    if output.exists():
        parser.error("output must be a new directory; existing data is never overwritten")
    output.mkdir(parents=True)
    reports = [capture(name, output, ffmpeg) for name in dict.fromkeys(args.scenes)]
    write_json(output / "environment.json", {"python": platform.python_version(), "platform": platform.platform(),
              "processor": platform.processor(), "mujoco": mujoco.__version__, "numpy": np.__version__,
              "script_sha256": sha256(Path(__file__)), "opengl_backend_request": os.getenv("MUJOCO_GL", "default"),
              "ffmpeg": subprocess.check_output([ffmpeg, "-version"], text=True).splitlines()[0],
              "scope": "Software-only illustrative simulations; not material identification, real-time benchmark or deployed Sim upgrade."})
    shutil.copyfile(HERE / "models" / "LICENSE", output / "UPSTREAM-LICENSE.txt")
    write_json(output / "summary.json", [{"scene": r["scene"], "encodings": r["encodings"], "final_measurement": r["final_measurement"]} for r in reports])


if __name__ == "__main__":
    main()