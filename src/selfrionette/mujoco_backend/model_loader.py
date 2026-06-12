from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MuJoCoModelBundle:
    model: object
    data: object
    model_path: Path


def _import_mujoco() -> object:
    import mujoco

    return mujoco


def default_fast_arm_scene_path() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "mujoco" / "fast_arm" / "scene.xml"


def load_mujoco_model(model_path: str | Path) -> MuJoCoModelBundle:
    path = Path(model_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    mujoco = _import_mujoco()
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    return MuJoCoModelBundle(model=model, data=data, model_path=path)
