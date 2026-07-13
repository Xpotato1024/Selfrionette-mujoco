from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FAST_ARM_INITIAL_KEYFRAME_NAME = "home"


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


def reset_mujoco_data_to_initial_state(
    model: object,
    data: object,
    *,
    model_path: str | Path,
) -> None:
    """Reset data, applying the canonical fast_arm named initial keyframe."""

    mujoco = _import_mujoco()
    resolved_path = Path(model_path).expanduser().resolve()
    if resolved_path == default_fast_arm_scene_path().resolve():
        keyframe_id = int(
            mujoco.mj_name2id(
                model,
                mujoco.mjtObj.mjOBJ_KEY,
                FAST_ARM_INITIAL_KEYFRAME_NAME,
            )
        )
        if keyframe_id < 0:
            raise ValueError(
                "canonical fast_arm initial keyframe is missing: "
                f"{FAST_ARM_INITIAL_KEYFRAME_NAME}"
            )
        mujoco.mj_resetDataKeyframe(model, data, keyframe_id)
    else:
        mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)


def load_mujoco_model(model_path: str | Path) -> MuJoCoModelBundle:
    path = Path(model_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    mujoco = _import_mujoco()
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    reset_mujoco_data_to_initial_state(model, data, model_path=path)
    return MuJoCoModelBundle(model=model, data=data, model_path=path)
