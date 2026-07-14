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
    from selfrionette.robots.fast_arm import FAST_ARM_ROBOT_PROFILE

    return FAST_ARM_ROBOT_PROFILE.mujoco_model_asset


def reset_mujoco_data_to_initial_state(
    model: object,
    data: object,
    *,
    model_path: str | Path,
    initial_keyframe_name: str | None = None,
) -> None:
    """Reset data, optionally applying an explicitly supplied named keyframe."""

    mujoco = _import_mujoco()
    if initial_keyframe_name is not None:
        keyframe_id = int(
            mujoco.mj_name2id(
                model,
                mujoco.mjtObj.mjOBJ_KEY,
                initial_keyframe_name,
            )
        )
        if keyframe_id < 0:
            raise ValueError(
                "configured initial keyframe is missing: "
                f"{initial_keyframe_name}"
            )
        mujoco.mj_resetDataKeyframe(model, data, keyframe_id)
    else:
        mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)


def load_mujoco_model(
    model_path: str | Path,
    *,
    initial_keyframe_name: str | None = None,
) -> MuJoCoModelBundle:
    path = Path(model_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    mujoco = _import_mujoco()
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    reset_mujoco_data_to_initial_state(
        model,
        data,
        model_path=path,
        initial_keyframe_name=initial_keyframe_name,
    )
    return MuJoCoModelBundle(model=model, data=data, model_path=path)
