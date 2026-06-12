from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from selfrionette.mujoco_backend.model_info import inspect_mujoco_model
from selfrionette.mujoco_backend.model_loader import default_fast_arm_scene_path, load_mujoco_model
from selfrionette.mujoco_backend.snapshot import snapshot_mujoco_state
from selfrionette.schemas import JointCommand
from selfrionette.schemas import MotionCommand, MuJoCoState


_FAST_ARM_JOINT_NAMES: tuple[str, ...] = (
    "sholder_joint_1",
    "sholder_joint_2",
    "sholder_joint_3",
    "elbow_joint",
)


@dataclass(slots=True)
class HeadlessMuJoCoSimulator:
    model: object
    data: object
    model_path: Path
    _frame_index: int = 0
    _last_dt_s: float | None = None
    _last_command: MotionCommand | None = None
    _pending_command: MotionCommand | None = None

    @classmethod
    def from_model_path(cls, model_path: str | Path) -> "HeadlessMuJoCoSimulator":
        bundle = load_mujoco_model(model_path)
        return cls(model=bundle.model, data=bundle.data, model_path=bundle.model_path)

    @classmethod
    def from_default_fast_arm(cls) -> "HeadlessMuJoCoSimulator":
        return cls.from_model_path(default_fast_arm_scene_path())

    def apply_command(self, command: MotionCommand) -> None:
        self._last_command = command
        self._pending_command = command

    @property
    def last_command(self) -> MotionCommand | None:
        return self._last_command

    @property
    def last_dt_s(self) -> float | None:
        return self._last_dt_s

    def _import_mujoco(self) -> object:
        import mujoco

        return mujoco

    def _resolve_joint_qpos_addresses(self) -> tuple[int, ...]:
        mujoco = self._import_mujoco()
        joint_names = inspect_mujoco_model(self.model).joint_names
        if joint_names != _FAST_ARM_JOINT_NAMES:
            raise ValueError(
                "unsupported fast_arm joint contract: "
                f"expected {_FAST_ARM_JOINT_NAMES}, got {joint_names}"
            )

        qpos_addresses: list[int] = []
        for joint_name in joint_names:
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            if joint_id < 0:
                raise ValueError(f"unknown joint name in model: {joint_name}")

            qpos_address = int(self.model.jnt_qposadr[joint_id])
            qpos_addresses.append(qpos_address)

        return tuple(qpos_addresses)

    def _apply_joint_command(self, joint_command: JointCommand) -> None:
        if joint_command.joint_velocities_rad_s:
            raise ValueError("joint velocities are not supported in this backend step")

        joint_angles = tuple(float(value) for value in joint_command.joint_angles_rad)
        qpos_addresses = self._resolve_joint_qpos_addresses()

        if joint_angles and len(joint_angles) != len(qpos_addresses):
            raise ValueError(
                "joint command length does not match fast_arm qpos contract: "
                f"expected {len(qpos_addresses)}, got {len(joint_angles)}"
            )

        if not joint_angles:
            return

        for qpos_address, angle in zip(qpos_addresses, joint_angles, strict=True):
            self.data.qpos[qpos_address] = angle

        self._import_mujoco().mj_forward(self.model, self.data)

    def step(self, dt_s: float) -> None:
        mujoco = self._import_mujoco()

        if self._pending_command is not None:
            command = self._pending_command
            if command.target is not None:
                raise ValueError("target commands are not supported in HeadlessMuJoCoSimulator")
            if command.joint is not None:
                self._apply_joint_command(command.joint)

        self.model.opt.timestep = dt_s
        mujoco.mj_step(self.model, self.data)

        if self._pending_command is not None and self._pending_command.joint is not None:
            self._apply_joint_command(self._pending_command.joint)

        self._last_dt_s = dt_s
        self._frame_index += 1

    def snapshot(self) -> MuJoCoState:
        return snapshot_mujoco_state(
            self.model,
            self.data,
            frame_index=self._frame_index,
        )
