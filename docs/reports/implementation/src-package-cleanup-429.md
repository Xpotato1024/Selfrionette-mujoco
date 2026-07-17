---
status: supporting
owner: architecture
last_verified: 2026-07-17
canonical_for: []
related:
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/429
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
---

# Issue #429 src package cleanup移行note

## 結果

fast_arm固有production implementationを`src/selfrionette/plugins/robots/fast_arm/`へ集約した。
generic `kinematics`はsolver Protocol、generic `mujoco_backend`はrobot-independentなmodel load、reset、
simulation、named reference / site extractionを所有する。runtime behavior、asset path、home keyframe、joint order、
solver parameter、payload、viewer、hardware経路は変更していない。

## ownership map

| 責務 | canonical owner |
|---|---|
| Profile / Runtime Plugin / Bundle / discovery entry | `plugins/robots/fast_arm/` |
| FK / IK / model-aligned tip FK | `plugins/robots/fast_arm/kinematics.py` |
| body / site name contractとvalidator | `plugins/robots/fast_arm/model_contract.py` |
| fast_arm endpoint wrapper | `plugins/robots/fast_arm/endpoint.py` |
| endpoint / Jacobian / neutral-pose diagnostics | `plugins/robots/fast_arm/diagnostics/` |
| generic solver Protocol | `kinematics/base.py` |
| generic MuJoCo primitive | `mujoco_backend/` |
| test-only doubles / pipeline builders | `tests/support/` |

## removed pathとreplacement

| removed path | replacement |
|---|---|
| `kinematics/fast_arm_endpoint.py`、`kinematics/fk.py`、`kinematics/ik.py` | `plugins/robots/fast_arm/kinematics.py` |
| `mujoco_backend/model_contract.py`内のfast_arm実装 | `plugins/robots/fast_arm/model_contract.py` |
| `mujoco_backend/fast_arm_compat.py`、`default_fast_arm_scene_path()`、`from_default_fast_arm()` | Profile resourceとplugin-owned explicit builder |
| `runtime/endpoint_motion_sanity.py`、`runtime/jacobian_mobility_diagnostics.py`、`runtime/neutral_initial_pose.py` | `plugins/robots/fast_arm/diagnostics/` |
| `robots/fast_arm.py`、`robot_registry.py`、旧`runtime/fast_arm_*.py`、旧registry module | plugin owner、`plugins/catalog.py`、`runtime/robot_provider_adapters.py` |
| `src/selfrionette/**/stubs.py` | `tests/support/*_doubles.py` |
| `build_noop_pipeline()`、stub-default `build_mujoco_pipeline()` | `tests/support/runtime_pipeline_builders.py` |

## public surface

- `selfrionette.kinematics`は`ForwardKinematicsSolver`と`InverseKinematicsSolver`だけを公開する。
- `selfrionette.mujoco_backend`はfast_arm固有constant、validator、endpoint wrapper、default scene helperを公開しない。
- `selfrionette.runtime`はfast_arm diagnostic、test builder、旧facade ownerを公開しない。
- fast_arm固有APIは`selfrionette.plugins.robots.fast_arm.*`からimportする。
- test doubleはproduction public APIではない。

retained compatibility exceptionはない。runtime package-rootのgeneric resolverはdeliberate logical APIとして維持し、
明示owner mappingから`plugins/catalog.py`へ直接解決する。

## behavior preservation

既知FK vector、IK→FK、MuJoCo `tip` site一致、model contract failure、Profile / Runtime Plugin / Bundle identity、
joint-limit、canonical initial state、bounded discovery、offline / viewer runtimeをregression testで維持する。
package pathはlogical experiment identityへ含まれないため、manifest identity、research claim、experiment conditionは
変更しない。

## side effect

hardware、serial、Arduino、OSC、robot output、deploymentは実行しない。
