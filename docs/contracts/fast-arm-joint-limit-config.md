---
status: canonical
owner: runtime
last_verified: 2026-07-13
canonical_for:
  - fast_arm TOML joint-angle limits and runtime qpos feasibility guard
related:
  - docs/architecture/runtime-composition.md
  - docs/contracts/runtime-input-safety.md
  - docs/operations/r7-e-p22-neutral-initial-pose.md
---

# fast_arm joint-limit configuration and qpos feasibility

## Configuration source of truth

`configs/fast_arm/joint_limits.toml` is the only joint-angle limit source of
truth. The fast_arm production composition owns loading it with Python 3.11
`tomllib`; input sources, kinematics, viewer, transport, generic pipelines,
and the MJCF do not read or duplicate the limits. The schema is version `1`,
identifies both `robot = "fast_arm"` and
`model = "fast_arm"`, requires `angle_unit = "rad"`, and records `status` as
`provisional` or `validated`.

The standard pre-identification configuration requires these joints in MuJoCo
order:

`sholder_joint_1`, `sholder_joint_2`, `sholder_joint_3`, `elbow_joint`.

All four standard values are `lower_rad = -pi` and `upper_rad = pi`, with
`status = "provisional"`. They are a conservative software feasibility
boundary before physical identification, not an authoritative mechanical
envelope. After physical identification, the TOML values and status are
updated; a motor-space or shoulder-coupled feasible region requires a separate
contract and is not inferred from these independent ranges.

## Startup validation

Before a fast_arm runtime pipeline starts, fast_arm production composition
parses and validates the TOML and checks the loaded MuJoCo model. Startup fails
when the
schema version, robot/model identity, unit, required joint set, joint order,
finite values, or `lower_rad < upper_rad` is invalid. The model joint names and
order must match the TOML, and the canonical MuJoCo `home` keyframe qpos must be
inside every configured range. There is no implicit `[-pi, pi]` fallback when
the file is missing or invalid.

## Enforcement boundary and semantics

The generic guard contract runs after the selected motion policy returns a
candidate command and before `MuJoCoSimulator.apply_command()` / `step()`.
Fast_arm production composition injects the fast_arm adapter into that
boundary. The generic and compatibility builders do not implicitly load this
TOML or apply fast_arm validation. The production programmed, replay,
keyboard/gamepad viewer, and fixture/loadcell paths all receive the same
injected fast_arm guard.

`QposFeasibilityResult.accepted` is the runtime accept/reject source of truth.
Command metadata is retained for diagnostics and compatibility observability;
robot-specific metadata is not a generic runtime control-flow contract.

The guard accepts exact lower and upper boundaries. If one or more candidate
qpos axes are outside the configured range, it rejects the entire candidate,
does not clamp individual axes, and applies a hold command containing the
current qpos. Typed `FastArmJointLimitViolation` values and compatible command
metadata expose the joint name, candidate value, lower/upper bounds, and
`qpos_feasibility_action = "hold_current_qpos"`.

Qpos-limit rejection is distinct from stale input, control-frame resolution
failure, and target rejection. It nevertheless suppresses target feedback
advancement for that step: the active/last-valid target and viewer rebase state
remain unchanged. The MuJoCo physical state remains the source of truth.

P24 replaces this explicit fast_arm composition seam with Robot Profile /
Runtime Plugin / Viewer Profile registries. The fast_arm plugin resolves this
same TOML through the profile declaration and injects the existing generic
guard boundary; no limit values are duplicated. Mesh collision,
self-collision, motor-space limits, torque/current/velocity safety, hardware
characterization, serial, OSC, and viewer config editing are outside this
contract.
