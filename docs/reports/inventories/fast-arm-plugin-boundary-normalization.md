---
status: historical
owner: architecture
last_verified: 2026-07-17
canonical_for: []
related:
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/423
  - docs/architecture/dependency-boundaries.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/experiment-plugin-composition.md
---

# #423 fast_arm plugin boundary inventory

このinventoryはbaseline main `e0311688f8d9738689434a82895616c42e965c0f`に対する
Issue #423時点のmigration判断を記録する。current ownershipとimport ruleの正本ではなく、
canonical文書とactual sourceを優先する。

| action | current owner / path | new owner | 主要consumer | allowed dependency | public API impact |
|---|---|---|---|---|---|
| move | `robots/fast_arm.py` | `plugins/robots/fast_arm/profile.py` | catalog、runtime plugin、model/profile compatibility | concrete profile -> generic `robot_profile` / domain model constants | 旧pathは同一constant / objectをre-export |
| move | `runtime/fast_arm_plugin.py` | `plugins/robots/fast_arm/runtime.py` | Bundle、fast_arm conformance | concrete runtime -> generic plugin contract、kinematics、motion、MuJoCo model contract、feasibility | 旧class / singleton objectを同一identityでre-export |
| move | `runtime/fast_arm_joint_limits.py` | `plugins/robots/fast_arm/feasibility.py` | Runtime Plugin、joint-limit tests | concrete feasibility -> generic qpos contract、MuJoCo model contract、Profile | 旧function / classを同一identityでre-export |
| move | `runtime/neutral_initial_pose.py`内のcanonical values / contract | `plugins/robots/fast_arm/initial_state.py` | Bundle、readiness、neutral-pose diagnostics | concrete declaration -> generic `InitialStateContract` | 旧bundle / neutral-pose exportは同一objectを維持 |
| move | `runtime/fast_arm_bundle.py` | `plugins/robots/fast_arm/bundle.py` | catalog、experiment composition、concrete pipeline | Bundle assembly -> concrete declarations + generic provider adapter / Bundle contract | 旧Bundle singletonを同一identityでre-export |
| generic adapter | `runtime/default_robot_providers.py` | `runtime/robot_provider_adapters.py` | Robot Bundle assembly、generic composition tests | generic adapter -> Profile / Runtime Plugin / typed provider contract | 旧provider classを同一identityでre-export。default selectionなし |
| generic primitive | `robot_registry.py`と`runtime/robot_plugin_registry.py`内のregistry / validation | `runtime/robot_resolution.py` | catalog、test-only registry injection、Robot Bundle validation | generic resolution -> Profile / Runtime Plugin contractだけ | `ImmutableRegistry`、`ResolvedRobotRuntime`、validatorを維持 |
| catalog | Profile / Runtime Plugin / Bundleの3 concrete registry | `plugins/catalog.py`のBundle registrationとprojection resolver | concrete pipeline、input step loop、offline smoke、#406 | application composition -> catalog -> Bundle | 4 resolver、registered ID API、error contractを維持 |
| generic public facade | `runtime/__init__.py`のmodule scan + `hasattr()` | 同fileのpublic name -> owner module / attribute明示mapping | root public API consumer | generic root ->明示owner。catalog-backed resolverだけcompatibility facade -> catalog | 全`__all__` entryと既存root object identityを維持 |
| runtime execution edge | input step loop plan / offline smokeの`ResolvedRobotRuntime`またはRuntime Plugin直接利用 | assembly時に解決した`EndpointPoseProvider`、`EndpointCommandProvider`、`QposFeasibilityProvider` | viewer step loop、replay/noop、offline smoke | composition root -> catalog -> typed provider。Plugin直接利用はmodel validation / FK factoryだけ | runtime plan shapeからbroad pluginを除去。既存step / smoke behaviorを維持 |
| compatibility facade | `robot_registry.py`、`robots/fast_arm.py`、旧`runtime/*registry.py`、`runtime/fast_arm_*.py`、`runtime/default_robot_providers.py` | 新ownerのre-export | legacy / public import compatibility test | facade -> catalogまたは新実装だけ | construction、factory、fallback、registrationを持たない |
| retain as domain algorithm | `kinematics/fast_arm_endpoint.py` | 同左 | Runtime Plugin、diagnostics、kinematics tests | concrete runtime integration -> kinematics。逆依存は禁止 | 変更なし |
| retain as domain contract | `mujoco_backend/model_contract.py` | 同左 | Runtime Plugin、feasibility、endpoint extraction | concrete runtime integration -> MuJoCo domain contract。backend -> plugin依存は除去 | 既存function / constantを維持 |
| retain | generic `motion/`、generic MuJoCo pipeline/backend、experiment contract / registry / manifest | 同左 | runtime / experiment composition | generic layerはcatalog / concrete pluginへ逆依存しない | 変更なし |
| retain | `runtime/neutral_initial_pose.py`のcandidate生成・診断algorithm | 同左 | diagnostic scripts / tests | fast_arm診断はplugin-owned canonical declarationを読む。Bundle assemblyへは依存しない | 既存function / classを維持 |
| compatibility helper | `mujoco_backend/model_loader.py::default_fast_arm_scene_path()`、`mujoco_backend/fast_arm_compat.py` | 同左 | legacy diagnostics、model/backend tests | この2 moduleだけ旧Profile facade importをallowlist。generic backendへの拡張は禁止 | 既存public helperを維持。新規composition APIではない |
| defer | `assets/mujoco/fast_arm/`、`configs/fast_arm/`、viewer profile、native viewer / diagnostic scripts | repository asset / config / presentation / tooling owner | Profile reference、operator / diagnostic path | asset/configはPython packageへ移動しない | pathとbehaviorを維持 |
| defer | #406 runner、R7-H contact plugin、viewer feature、hardware / serial / OSC | 後続Issue | 後続composition / operator | #423のcatalog / typed provider boundaryだけを利用 | 本Issueでは実装しない |

## final resolution flow

```text
plugins/catalog.py
  -> resolve_robot_bundle("fast_arm")
  -> bundle.profile
  -> bundle.runtime_plugin
  -> assembly-time typed provider
```

`resolve_robot_profile()`、`resolve_robot_runtime_plugin()`、`resolve_robot_runtime()`は上記Bundleの
同一Profile / Runtime Plugin objectへ収束する。catalogは`FAST_ARM_ROBOT_BUNDLE`だけを具体登録し、
Profile / Runtime Pluginの別assemblyまたはimplicit fallbackを持たない。
application compositionはBundleからtyped providerを取得した後、runtime planへproviderだけを注入する。
step loopとoffline smokeはendpoint pose、motion command、qpos feasibilityをRuntime Pluginへ直接問い合わせない。

## #406 handoff

#406はcatalog、resolved experiment composition、typed provider contractを使用できる。
`plugins.robots.fast_arm.*`とcompatibility facadeは直接importせず、Bundleをruntime service locatorにしない。
`DefaultRobot`、`DEFAULT_ROBOT_BUNDLE`、dynamic discovery、implicit fast_arm fallbackは存在しない。
