---
status: historical
owner: architecture
last_verified: 2026-07-18
canonical_for: []
related:
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/443
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/444
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/445
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/446
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/447
  - https://github.com/Xpotato1024/Selfrionette-mujoco/issues/448
  - docs/architecture/dependency-boundaries.md
  - docs/contracts/assets.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
---

# #444 fast_arm core ownership inventory

## 目的とbaseline

この文書は、Issue #444で実施したbehavior-preservingなarchitecture inventoryである。
baselineは`origin/main`の`678c25d65a627cd612b4293c9160bf459ef8d5fe`で、2026-07-18に
`git ls-files`、`git grep`、`rg`を使い、source、resource、config、fixture、test、script、docs、CI、
subprocess / CLI、viewer VFSとpublic URLのconsumerを追跡した。current contractの正本は
`docs/README.md`から辿れるcanonical文書とactual sourceであり、このinventoryは#445以降の移行判断を固定する。

棚卸し範囲はproduction module 15件、asset / config 11件、fast_arm名を持つtest 17件、
fast_arm moduleを直接importする追加test 36件、literal / facade / conformanceから参照する追加test 12件
（viewer testを含む計65件）、関連script 11件、およびcanonical / operation docsである。
`legacy/fast_arm_control/`は参照専用であり、移行元または実行対象に含めない。

## 1. Current state

production discoveryは次の一本道である。

```text
selfrionette.plugins.robot_discovery
  -> <robot package>.plugin
  -> plugin.py::ROBOT_PLUGIN
  -> FAST_ARM_ROBOT_BUNDLE
  -> Profile / Runtime Plugin / typed providers
  -> runtime composition
```

`src/selfrionette/plugins/robots/fast_arm/plugin.py`の`ROBOT_PLUGIN`だけをproduction discovery入口とする。
package root `__init__.py`は具体objectをexportしない。個別moduleの`__all__`は現在のmodule-level public surfaceであり、
移動中もroot入口を増やさず、必要なcompatibility re-exportは旧moduleに閉じる。

resourceは`assets/mujoco/fast_arm/`と`configs/fast_arm/`にあり、`plugin.py`がrepository-relative pathを宣言する。
`profile.py`と`viewer.py`は`Path(__file__).resolve().parents[5]`でrepository rootを計算する。editable checkoutでは
両resourceが存在することを確認した。一方、`pyproject.toml`は`src` package discoveryだけを指定し、XML、STL、JSON、
TOMLのpackage-dataを宣言しない。このため通常のwheel/installはrepository-root resourceを同梱せず、現行resolverは
installed packageで成立する保証がない。CIはcheckout + `uv sync`のeditable環境を検証するが、wheel/install smokeはない。

viewerは`viewer-profile.json`の`modelUrl`、fixture URL、VFS mappingを読み、Viteの`publicDir`としてrepository
`assets/`を公開する。browserはMuJoCo WASMをrenderingに使うが、Python runtime / payloadとMuJoCo physical stateがSoTであり、
viewerはfast_arm core implementation、FK、IK、安全判定を参照しない。

## 2. Ownership principles

| 区分 | ownership rule |
|---|---|
| shared core | Python-onlyの独立package `fast_arm_core`。Selfrionette schema / runtime / backendに依存しないrobot identity、joint / unit / frame spec、数式、limit data、initial pose definition、`arm.xml`、mesh、simulator非依存fixture |
| Selfrionette adapter | core valueをgeneric Protocol / schema / RobotBundle / Profile / Runtime Plugin / typed provider / resource declaration / viewer declarationへ接続する変換とvalidator、およびMuJoCo `scene.xml` |
| integration | MuJoCo site、runtime、payload、viewer、CLIを複数layerにまたがって照合する診断・test。coreへ移さない |
| repository operation | CLI wrapper、fixture export、viewer operation、hardware operation、CI、migration / validation docs。production library APIにしない |
| generic ownerに維持 | generic FK/IK Protocol、schema、MuJoCo primitive、motion、runtime composition、transport、viewer renderer、catalog / discovery contract |

coreの公開Python package identityは`fast_arm_core`であり、Selfrionette namespaceへ所属させない。
coreはSelfrionetteをimportしない。adapterだけが`fast_arm_core`とSelfrionette contractの両方を参照する。
robot固有の数式、定数、resource pathをadapterへ複製せず、adapterはcore representationを変換する。

## 3. Complete inventory

### 3.1 Production source

| current path | item / responsibility | current consumers | current owner | proposed owner / kind | migration | rationale | compatibility risk |
|---|---|---|---|---|---|---|---|
| `fast_arm/__init__.py` | side-effect-free namespace | importer / discovery package scan | plugin package | root namespace / adapter | #445 | concrete exportを増やさない | import side effect |
| `plugin.py` | `ROBOT_PLUGIN`、resource declaration | discovery、catalog、architecture tests | plugin entry | root `plugin.py` / adapter | #445で維持 | 唯一のproduction entry | discovery / identity |
| `bundle.py` | Bundleとtyped provider assembly | plugin、catalog projection、experiment composition | plugin | `adapter/bundle.py` / adapter | #445 | generic providerへの接続 | object identity / public import |
| `profile.py` | joint order、model/config path、unit、endpoint、capability | runtime、bundle、scripts、runtime/backend tests | plugin | `adapter/profile.py` / adapter | #445 | core spec/resourceを`RobotProfile`へ変換 | path / metadata |
| `runtime.py` | solver、motion、guard、endpoint accessor、simulator builder | Bundle provider、runtime composition、tests | plugin | `adapter/runtime.py` / adapter | #445 | coreをSelfrionette runtimeへ接続 | behavior / factory identity |
| `viewer.py` | JSON decodeとViewer declaration | plugin、profile、viewer compatibility tests | plugin | `adapter/viewer.py` / adapter | #445 | viewer contractはSelfrionette側 | URL / digest / VFS |
| `endpoint.py` | generic state/referenceからfast_arm endpoint抽出 | diagnostics、runtime/backend tests、startup script | plugin | `adapter/endpoint.py` / adapter | #445 | MuJoCoState / backend contract依存 | fallback / frame |
| `feasibility.py` | TOML parse、model照合、runtime guard | runtime、joint-limit tests | plugin | pure parse/specは`core/joint_limits.py`、guard変換は`adapter/feasibility.py` | #445 | data ruleとSelfrionette guardを分離 | reject/hold semantics |
| `initial_state.py` | initial valuesと`InitialStateContract` | Bundle、readiness、diagnostics、tests | plugin | canonical definitionは`core/src/fast_arm_core/reference/initial_state.py`、contractは`adapter/initial_state.py` | #445 | core SoTとschema projectionを分離 | exact float / identity |
| `kinematics.py` | solver-local FK/IK、model-aligned FK、geometry / ref定数、Selfrionette schema result | runtime、diagnostics、kinematics/motion/runtime tests | plugin | pure calculation/resultは`core/src/fast_arm_core/{kinematics,model_kinematics}.py`、generic Protocol/schema wrapperは`adapter/kinematics.py` | #445 | `fast_arm_core` resultとSelfrionette `JointCommand` / `Vector3`を分離 | frames / exact convergence / class identity |
| `model_contract.py` | model/body/site namesとbackend validator | profile、endpoint、runtime、feasibility、tests | plugin | pure namesは`core/src/fast_arm_core/model_spec.py`、backend validatorは`adapter/model_contract.py` | #445 | name SoTとMuJoCo adapterを分離 | error / fallback semantics |
| `diagnostics/endpoint_motion_sanity.py` | runtime / solver / site / trajectory診断 | script、runtime tests | plugin | `adapter/diagnostics/` / integration | #445、testは#446 | cross-layerでcore単体ではない | report fields / exit semantics |
| `diagnostics/jacobian_mobility.py` | MuJoCo / motion policy Jacobian診断 | script、runtime tests | plugin | `adapter/diagnostics/` / integration | #445、testは#446 | runtime/MuJoCo依存 | tolerance / labels |
| `diagnostics/neutral_initial_pose.py` | model / limit / collision evidence / pose評価 | scripts、runtime tests | plugin | `adapter/diagnostics/` / integration | #445、testは#446 | core referenceとruntime evidenceを接続 | ranking / evidence |
| `diagnostics/__init__.py` | diagnostics namespace | scripts/tests | plugin | `adapter/diagnostics/__init__.py` / integration | #445 | diagnosticsをlibrary coreから分離 | import path |

### 3.2 Resource、config、fixture

| current path | item / responsibility | current consumers | current owner | proposed owner / kind | migration | rationale | compatibility risk |
|---|---|---|---|---|---|---|---|
| `assets/mujoco/fast_arm/arm.xml` | joint axis/ref、body/link、inertial、actuator、`home`、`tip` | scene include、Python/WASM model load、FK/site tests | asset | `core/src/fast_arm_core/resources/model/arm.xml` / core representation | #445 | shared robot model。`home`はcore initial pose definitionのprojection | include path / names / qpos |
| `assets/mujoco/fast_arm/scene.xml` | `arm.xml` include、visual quality、skybox、ground texture/material、light、floor | Profile、plugin、loader、viewer、scripts/tests | asset | `adapter/resources/mujoco/scene.xml` / adapter | #445 | Selfrionette MuJoCo sceneでありshared robot coreではない | public URL / include / model load |
| `assets/mujoco/fast_arm/meshes/*.stl`（5件） | robot geometry | MJCF、viewer VFS、asset tests | asset | `core/src/fast_arm_core/resources/model/meshes/` / canonical | #445 | shared robot geometry | filename case / binary integrity |
| `assets/mujoco/fast_arm/viewer-profile.json` | viewer serialization、URL/VFS/style/joint projection | viewer adapter、plugin、TS facade/tests | asset | `adapter/resources/viewer-profile.json` / adapter | #445 | rendering declarationはSelfrionette contract | digest / public URL |
| `assets/mujoco/fast_arm/fixtures/fast_arm_sweep_x_qpos.json` | runtime-generated qpos viewer fixture | viewer tests/demo、export script | asset | `adapter/resources/fixtures/` / integration-derived | #445 | payload/runtime metadataを含みcore単体fixtureではない | exact bytes / metadata |
| `configs/fast_arm/joint_limits.toml` | software qpos limit data | profile、plugin、feasibility、tests/docs | config | `core/src/fast_arm_core/resources/config/joint_limits.toml` / canonical | #445 | robot固有limit SoT | path / reject behavior |
| `assets/mujoco/fast_arm/README.md` | robot modelとMuJoCo sceneをまとめたasset usage note | human / docs links | asset docs | `adapter/resources/README.md`相当 / documentation | #445 | core modelとadapter sceneのassembly手順を記録 | stale command/path/ownership |

`legacy/fast_arm_control/mujoco_sim/`とzip内には同名XMLがあるが参照専用duplicateである。#445はcopy元にせず、
現行canonical assetだけを移す。fixtureはsimulator非依存referenceではなくruntime/viewer integration evidenceなのでcoreへ入れない。

### 3.3 Test、script、documentation、CI

| current path | item / responsibility | current consumers | current owner | proposed owner / kind | migration | rationale | compatibility risk |
|---|---|---|---|---|---|---|---|
| `tests/assets/test_fast_arm_assets.py` | XML/STL/include/model integrity | pytest / CI | asset test | core test | #446 | resource単体検証 | moved resource path |
| `tests/kinematics/test_fast_arm_endpoint.py` | FK/IK pure behavior | pytest / CI | kinematics test | core test | #446 | pure fast_arm algorithm | numeric tolerance |
| `tests/robots/fast_arm_conformance_case.py` | generic conformance data case | conformance/runtime tests | test support | adapter test support | #446 | Bundle/Profile/Runtime適合 | import path |
| `tests/runtime/test_fast_arm_plugin_catalog.py` | discovery、Bundle、resource、viewer declaration | pytest / CI | runtime test | adapter test | #446 | Selfrionette registration contract | object identity / URL |
| `tests/runtime/test_fast_arm_joint_limits.py` | parser/model/guard/hold integration | pytest / CI | runtime test | core parse cases + adapter guard cases | #446 | pure dataとruntime semanticsを分離 | coverage loss |
| `tests/runtime/test_fast_arm_{endpoint_motion_sanity,endpoint_diagnostic_logging,endpoint_trajectory_diagnostics,endpoint_trajectory_export}.py` | diagnostic/log/export contract | pytest / CI | runtime test | integration test | #446 | 複数layer evidence | output fields |
| `tests/runtime/test_fast_arm_{fk_site_consistency,ik_fk_sanity,solver_mujoco_frame_alignment}.py` | solver / MuJoCo frame/site照合 | pytest / CI | runtime test | integration test | #446 | coreとphysical modelの境界 | frame / tolerance |
| `tests/runtime/test_fast_arm_{initial_tip_workspace_diagnostics,jacobian_mobility_diagnostics,joint_axis_mapping_diagnostics,local_jacobian_dof_allocation,viewer_endpoint_workspace_diagnostics}.py` | model/runtime/viewer診断 | pytest / CI | runtime test | integration test | #446 | core単体でない | diagnostic semantics |
| `tests/runtime/test_neutral_initial_pose.py` | initial contractとmodel diagnostic | pytest / CI | runtime test | adapter + integration test | #446 | schemaとphysical evidenceの両方 | exact values |
| generic testsのfast_arm conformance利用（後述） | generic APIへproduction fixtureを当てる | pytest / CI | 各generic layer | generic ownerに維持 | #446では移動しない | generic behavior ownershipを守る | fixture import更新のみ |
| `scripts/export_wasm_qpos_fixture.py` | runtime fixture生成 | operator、script test、viewer fixture | scripts | Selfrionette integration diagnostic | #448 | payload/runtime由来 | output bytes/path |
| `scripts/run_fast_arm_endpoint_motion_sanity.py` | diagnostic CLI | operator/docs/tests | scripts | Selfrionette integration diagnostic | #448 | adapter diagnostic wrapper | args/exit/output |
| `scripts/run_fast_arm_jacobian_mobility_diagnostics.py` | diagnostic CLI | operator/docs/tests | scripts | Selfrionette integration diagnostic | #448 | adapter diagnostic wrapper | args/exit/output |
| `scripts/run_fast_arm_neutral_pose_evaluator.py` | pose evaluator CLI | operator/docs/tests | scripts | Selfrionette integration diagnostic | #448 | model/runtime evaluation | args/exit/output |
| `scripts/run_fast_arm_neutral_pose_startup_smoke.py` | runtime/viewer first-input smoke | operator/docs/tests | scripts | integration diagnostic | #448 | cross-layer startup | payload/exit |
| `scripts/plot_fast_arm_endpoint_trajectory_log.py` | CSV plot | operator/evidence | scripts | repository operation | #448 | artifact rendering utility | CLI/output |
| `scripts/view_fast_arm_native_mujoco.py` | native viewer / model info | operator/docs | scripts | viewer operation | #448 | GUI/operator boundary | GUI / model path |
| `scripts/run-browser-viewer-smoke.ps1`、`run_live_viewer_smoke.py` | viewer operation | operator/docs | scripts | viewer operation | #448 | robot coreではない | subprocess/ports |
| `scripts/run_replay_mujoco_{dry_run,websocket_publisher}.py` | generic compatibility CLI | operator/docs | scripts | compatibility wrapper | #448 | canonical CLIへの移行対象 | args/exit/network |
| `apps/mujoco-viewer/src/robot-profiles/fastArm.ts` | 未接続時のfast_arm declaration URL facade | `robot-profiles/registry.ts` -> product viewer / tests | viewer compatibility | Selfrionette adapter compatibility facade | #445 | declaration内容を再定義せずstable URLだけを読む | public URL / fallback |
| `apps/mujoco-viewer/src/robot-profiles/declaration.ts` | generic resource path / URL decode、digest、compatibility | product viewer、viewer tests | generic viewer | generic ownerに維持 | #445でpackage resource binding対応 | fast_armを直接importしない | schema / fail-closed behavior |
| `apps/mujoco-viewer/vite.config.ts` | repository `assets/`のpublic配信 | Vite dev/build、viewer test | repository/viewer operation | generic viewer operation | #445でpackage resource route対応 | core実装をviewerから参照させない | clean build / URL |
| `pyproject.toml` | root Python package discovery / package-data状態 | build backend、`uv sync`、install | repository packaging | repository operation | #445 | rootから`fast_arm_core`を導入する方式を選び、core側`pyproject.toml`がXML/STL/TOML package-dataを所有 | installed resource/import欠落 |
| `.github/workflows/ci.yml` | checkout/editable suites | GitHub Actions | repository | repository operation | #445/#446で必要時同期 | installed smokeは現在なし | clean install gap |
| `docs/architecture/dependency-boundaries.md` | import / core-adapter dependency rule | source、architecture tests、human | architecture | generic ownerに維持 / canonical | #444で最小更新、#445でactual path照合 | dependency directionの正本 | stale boundary |
| `docs/contracts/assets.md` | MJCF/STL/resource ownership contract | registration、asset tests、human | architecture | generic resource contract + adapter projection / canonical | #445 | resource path / include / URL rule | stale physical path |
| `docs/contracts/robot-profile-runtime-viewer-profile.md` | registration/Profile/Runtime/Viewer contract | adapter、runtime/viewer tests、human | architecture | generic contract ownerに維持 / canonical | #445 | adapter projectionの正本 | identity / URL / payload |
| `docs/contracts/kinematics-command-contract.md` | generic solver / command境界 | kinematics/motion/runtime、tests | contracts | generic ownerに維持 / canonical | #445 | concrete fast_armをgenericへ戻さない | schema / command semantics |
| `docs/contracts/forward-kinematics.md` | FK Protocolとfast_arm physical FK ownership | core/adapter、FK/site tests | contracts | generic contract + core implementation / canonical | #445 | solver-local / physical frameを区別 | frame / path |
| `docs/contracts/inverse-kinematics.md` | IK baseline / failure contract | core/adapter、IK tests | contracts | generic contract + core implementation / canonical | #445 | solver behaviorを固定 | tolerance / failure |
| `docs/contracts/fast-arm-joint-limit-config.md` | TOML SoT / qpos guard semantics | core/adapter、runtime tests | runtime contract | core data + adapter guard contract / canonical | #445 | valueとhold semanticsを分離 | path / safety semantics |
| `docs/contracts/mujoco-model-name-contract.md` | fast_arm body/site/fallback contract | core model spec、adapter validator、tests | architecture | core spec + adapter contract / canonical | #445 | name/valueを一ownerへ統合 | missing/fallback errors |
| `src/selfrionette/kinematics/README.md` | generic kinematics package role | package maintainer、architecture tests | generic kinematics docs | generic ownerに維持 / canonical package note | #444で修正 | Protocol-only ownershipを明示 | concrete code drift |
| `docs/reports/inventories/fast-arm-plugin-boundary-normalization.md` | #423時点のplugin migration snapshot | architecture review / human | historical | historicalのまま / evidence | 変更しない | current SoTではない | stale snapshot誤用 |
| `docs/reports/implementation/src-package-cleanup-429.md` | #429 cleanup result / removed path evidence | architecture review / human | historical | historicalのまま / evidence | 変更しない | current owner追跡のprovenance | history rewrite |
| `docs/reports/README.md` | inventoryへのindex | human / docs validator | reports index | repository documentation operation | #444で最小更新 | current SoT mapへinventoryを混入させない | broken link |
| historical reports / archived operations | provenance | human | historical | historicalのまま | 原則変更しない | current SoTではない | history rewrite |

## 4. Source-of-truth matrix

| subject | current canonical owner | duplicate / derived representation | future owner in #445 | consolidation rule |
|---|---|---|---|---|
| robot identity/version | `plugin.py` registration + Bundle `VersionedIdentity` | Profile ID、viewer profile ID/model version、fixture metadata | `fast_arm_core` definition + adapter registration | core package identity、robot logical version、registration schema versionを混同しない |
| joint names/order | `arm.xml`とresolved Profileの一致 | TOML sections、viewer JSON、fixture metadata、tests | core model/spec、adapterはprojection | coreから生成/照合し値を複製しない |
| joint axes | `arm.xml` | `kinematics.py` model-aligned body chain、diagnostic期待値、historical report | core model + model-aligned FK | #445でcore ownerへ統合し値は不変 |
| units/frame | Profile coordinate contract、MJCF、solver contract | viewer JSON、fixture metadata、initial contract | core spec + adapter projection | solver-localとMuJoCo worldを区別 |
| joint-space / motor-space | productionはMuJoCo qposとsolver-local conventionのみ。`sholder_joint_2` ref変換はmodel/solverで表現 | historical docsの未確定motor mapping | core convention spec | motor-space変換は未実装のまま。#445で新規behaviorを作らない |
| link parameters | `kinematics.py`のsolver-local `(0.26,0.24,0.23)`、physical geometryはMJCF | model-aligned FK内にMJCF body/site値の複製 | core solver spec + core model resource | solver-localとphysical modelを別representationとして明示し、model値の手書きduplicateを#445で一ownerへ寄せる |
| FK | `kinematics.py` | solver-local FKとmodel-aligned pure FKの2用途 | core kinematics | frame/provenance別APIを維持 |
| IK | `kinematics.py` | diagnostics / fixture qposはderived | core kinematics | tolerance、failure、seed continuity不変 |
| feasibility | TOML + `feasibility.py` accepted/reject logic | diagnostic metadata | core limit parse/spec + adapter guard | accepted bool / hold semanticsはadapter contract |
| joint limits | `configs/fast_arm/joint_limits.toml` | docs、test literals | core resource TOML | test literalはinvalid-case fixtureだけ許可 |
| initial poses | 現在は`arm.xml` `home`と`initial_state.py`に重複 | MJCF home、Selfrionette `InitialStateContract`、reference qpos fixture、expected endpoint/orientation、viewer metadata | `fast_arm_core` initial pose definition | #445で現行MJCF値をcore definitionへ移し、MJCF/contract/fixture/metadataをprojectionとして完全一致させる |
| endpoint frame | physicalはMuJoCo world `tip`、solver-localは`base_link` | Profile、model contract、runtime adapters | core frame spec + adapter endpoint | 自動同一視しない |
| MuJoCo model names | `model_contract.py` + MJCF一致 | Profile、docs/tests | core model spec + adapter validator | fallbackはexplicit opt-in |
| geometry/mesh | `arm.xml` + STL | viewer compiled geometry | `fast_arm_core` resources | browser独自geometry SoTを作らない |
| robot MJCF | `arm.xml` | model-aligned FKのhand-coded transform | `fast_arm_core` resource | transform定数をcore model specへ集約 |
| MuJoCo scene | `scene.xml` | visual quality、skybox、ground、light、floorと`arm.xml` include | adapter resource。floor等は将来scene/task ownerへ分離可能 | robot coreへ含めず、include先のcore bytesとの整合を検証 |
| viewer profile | `viewer-profile.json` | decoded Python/TS objects、TypeScript URL facade | adapter resource | coreをviewerからimportしない |
| viewer VFS resources | viewer JSON mapping + registration equality | Vite `publicDir` route、tests | adapter declaration referencing core resources | URLは維持しresource registry経由で配信 |
| reference qpos | XML `home`、viewer fixture frames | initial contract、tests | `fast_arm_core` initial pose definition | XML/contract/fixtureをderived representationとしてexact comparison |
| reference FK | initial contract tip/orientation、FK/site tests | docs report values | `fast_arm_core` reference definition / derived fixture | solver-localとMuJoCo worldのframe/provenanceを分けて完全一致を検証 |
| diagnostics fixtures | runtime-generated viewer JSON、test expected dicts | logs / reports | adapter/integration | core fixtureと混在させない |

#445ではinitial poseのfloat値、joint order、frame、endpoint、orientationをprojection間で暗黙変換しない。
XML、Python definition、fixture、viewer metadataのいずれかが不一致ならfail closedする。

## 5. Proposed in-repository structure

#445は空directoryやskeletonを先行作成せず、実体を次の順に移す。

```text
src/selfrionette/plugins/robots/fast_arm/
├── __init__.py
├── plugin.py                         # 唯一のproduction discovery entry
├── adapter/
    ├── __init__.py
    ├── bundle.py
    ├── profile.py
    ├── runtime.py
    ├── kinematics.py                 # generic FK/IK Protocol、schema adapter
    ├── viewer.py
    ├── endpoint.py
    ├── feasibility.py
    ├── initial_state.py
    ├── model_contract.py
    ├── diagnostics/{endpoint_motion_sanity,jacobian_mobility,neutral_initial_pose}.py
    └── resources/
        ├── mujoco/scene.xml
        ├── viewer-profile.json
        └── fixtures/fast_arm_sweep_x_qpos.json
└── core/                              # 将来の独立repository mount point
    ├── pyproject.toml
    ├── src/
    │   └── fast_arm_core/
    │       ├── __init__.py
    │       ├── definition.py
    │       ├── kinematics.py
    │       ├── model_kinematics.py
    │       ├── model_spec.py
    │       ├── joint_limits.py
    │       ├── reference/
    │       │   └── initial_state.py          # canonical initial pose definition
    │       └── resources/
    │           ├── model/{arm.xml,meshes/...}
    │           └── config/joint_limits.toml
    └── tests/                         # 実体移動は#446
```

`core/`直下に`__init__.py`を置かず、`core/`自体をSelfrionette Python packageにしない。shared APIのimportは
`from fast_arm_core import ...`であり、`from selfrionette.plugins.robots.fast_arm.core import ...`を使用しない。
物理配置はplugin package内のmount pointだが、Python package identityはSelfrionette namespaceから独立する。

`adapter/kinematics.py`は`fast_arm_core`のpure resultを`Vector3` / `JointCommand`へ変換し、generic
`ForwardKinematicsSolver` / `InverseKinematicsSolver`を満たす現在のclassを所有する。旧
`fast_arm/kinematics.py`は#445の移行中だけadapter classとcore constantをthin re-exportし、class / function identityを
維持する。ほかの旧module pathも限定re-exportだけとし、別factory、fallback、registrationを持たせない。
恒久public surfaceの要否はexisting `__all__`とactual external consumerを基準に#445で検証するが、`plugin.py`以外を
discovery入口にはしない。

## 6. Dependency boundary

```text
generic Protocol / schema / composition contract
                    <- adapter <- plugin.py / ROBOT_PLUGIN
fast_arm_core       <- adapter
```

許可:

- `fast_arm_core` -> Python標準library、明示済み数値dependency、core内module / resource
- adapter -> `fast_arm_core` + generic Selfrionette contract / primitive
- plugin.py -> adapter assemblyだけ
- runtime composition -> catalog / registrationから得たtyped provider

禁止:

- `fast_arm_core` -> `selfrionette`
- generic layer / catalog /他robot -> fast_arm core
- viewer -> fast_arm core implementation
- core -> runtime、MuJoCo backend adapter、transport、CLI、experiment / evaluation
- adapterでrobot固有数式、定数、resource pathを再定義
- `selfrionette.plugins.robots.fast_arm.core`をshared import APIにすること
- `__init__.py`副作用登録、coreからの第二production entry、runtime `sys.path`変更

MuJoCoはphysical state SoT、browser viewerはrendering-onlyを維持する。

## 7. Resource boundary

### #445: 同一repository段階

- shared resource実体は`core/src/fast_arm_core/resources/`、MuJoCo `scene.xml`、viewer declaration、runtime fixtureは
  `adapter/resources/`へ所有を寄せる。`scene.xml`はadapterからcore-owned `arm.xml`をincludeする。
- `fast_arm_core`は独立したPython-only packageとし、installed/editable/wheelの全形態で同じpackage identityとAPIを使う。
- root projectからの導入方式をpath dependency、workspace、package discoveryのどれにするかは#445で実測して決める。
  runtimeの`sys.path`変更は使わない。
- Pythonは`importlib.resources`相当のpackage resource APIでinstalled/editableの双方を解決する。
- #445ではcore側`pyproject.toml`のpackage-dataを設定し、wheelにXML/STL/TOMLが含まれることをtestする。
- MuJoCo include / mesh relative pathを維持する。materialized filesystem pathが必要なAPIではresource contextの寿命を明示する。
- generic resource contractへpackage resourceを表すtyped declarationをadditiveに追加し、adapterがcore package / relative
  resourceと既存のlogical public pathを一対一でbindする。generic resolverはrobot IDからpackage pathを推測しない。
- viewer JSONの既存`resourcePath`とpublic URLはcompatibility identifierとして維持し、adapterのbindingから同じpackage
  resource bytesを配信する。VFS path、URL、declaration digestを変更せず、旧`assets/`にfallback copyを残さない。

### #447: 独立repository段階

- #447までは外部repository、submodule、subtree、vendor copyを導入しない。
- #447後もSelfrionette側の`fast_arm/core/`mount point、`fast_arm_core` package identity、adapter import/APIを維持する。
- `core/`directory全体を別repositoryまたは固定revisionの外部checkoutへ置換しても、adapterの
  `from fast_arm_core import ...`を変更しないことを成功条件とする。
- submodule / pinned snapshot / subtree / release archiveの最終選択、repository名、visibility、ownershipは#447で決める。
- runtime network fetch、floating revision、duplicate fallback copyは禁止する。
- Rust、C++、openFrameworks、native binaryまたはmulti-language packageは#447の必須成果に含めない。
  Python-only coreを運用・検証した後、必要なら別Issueで判断する。

## 8. Test ownership map

### #446で移すtest

| destination | current tests |
|---|---|
| core | `tests/assets/test_fast_arm_assets.py`、`tests/kinematics/test_fast_arm_endpoint.py`、joint-limit parser/data cases、model spec / initial reference exactness |
| adapter | `tests/runtime/test_fast_arm_plugin_catalog.py`、joint-limit guard cases、`tests/robots/fast_arm_conformance_case.py`を使うProfile / Runtime / Bundle / provider conformance |
| integration | `test_fast_arm_endpoint_diagnostic_logging.py`、`test_fast_arm_endpoint_motion_sanity.py`、`test_fast_arm_endpoint_trajectory_diagnostics.py`、`test_fast_arm_endpoint_trajectory_export.py`、`test_fast_arm_fk_site_consistency.py`、`test_fast_arm_ik_fk_sanity.py`、`test_fast_arm_initial_tip_workspace_diagnostics.py`、`test_fast_arm_jacobian_mobility_diagnostics.py`、`test_fast_arm_joint_axis_mapping_diagnostics.py`、`test_fast_arm_local_jacobian_dof_allocation.py`、`test_fast_arm_solver_mujoco_frame_alignment.py`、`test_fast_arm_viewer_endpoint_workspace_diagnostics.py`、`test_neutral_initial_pose.py` |

### generic ownerに残すtest

次はfast_armをproduction conformance fixtureとして使用するが、検証責務はgeneric ownerにあるため移動しない。

- architecture: `test_kinematics_test_double_boundaries.py`、`test_robot_plugin_catalog_boundaries.py`、
  `test_robot_profile_boundaries.py`、`test_src_package_cleanup_boundaries.py`、
  `test_experiment_plugin_boundaries.py`、`test_robot_runtime_plugin_conformance_boundaries.py`、
  `test_docs_sot.py`、`test_script_inventory_boundaries.py`
- kinematics / motion: `test_inverse_kinematics_solver.py`、`test_target_to_joint_motion_generator.py`
- MuJoCo backend: `test_endpoint_extraction.py`、`test_headless_simulator.py`、`test_headless_simulator_control.py`、
  `test_model_contract.py`、`test_model_info.py`、`test_model_loader.py`、`test_qpos_command_adapter.py`、`test_snapshot.py`
- runtime / CLI / composition: `test_cli.py`、`test_concrete_mujoco_pipeline.py`、`test_evaluation_manifest.py`、
  `test_experiment_plugin_composition.py`、`test_generic_qpos_feasibility_boundary.py`、`test_input_step_diagnostics.py`、
  `test_jacobian_mobility_diagnostics.py`、`test_live_input_stale_command_safety.py`、`test_local_endpoint_motion_policy.py`、
  `test_mujoco_pipeline.py`、`test_r7_b_offline_input_runtime_stepping_smoke.py`、`test_replay_mujoco_dry_run_entry.py`、
  `test_replay_mujoco_pipeline.py`、`test_replay_mujoco_target_qpos_smoke.py`、`test_replay_mujoco_transport_pipeline.py`、
  `test_replay_mujoco_websocket_publisher.py`、`test_robot_plugin_discovery.py`、`test_robot_profile_registry.py`、
  `test_runtime_input_source_step_loop.py`、`test_runtime_stub_guardrails.py`、`test_viewer_input_source_step_loop.py`
- conformance support: `tests/robots/robot_runtime_plugin_conformance_cases.py`、
  `tests/support/test_robot_runtime_plugin_conformance.py`
- script: `tests/scripts/test_export_wasm_qpos_fixture.py`
- viewer: `apps/mujoco-viewer/tests/mujocoQposSync.test.ts`、`robotProfileRegistry.test.ts`、
  `productViewerEntrypoint.test.ts`、`visualStyles.test.ts`、`viteConfig.test.ts`と`testViewerProfile.ts`

#446は配置だけでcoverage、fixture semantics、test selectionを弱めない。core testは将来外部repositoryへそのまま移せること、
adapter / integration testはSelfrionette repositoryに残ることをgateにする。

## 9. Script ownership map

| classification | scripts | #448 disposition |
|---|---|---|
| core validation候補 | 現在なし。pure FK/IK/resource validationはpytestが所有 | 必要ならcore側のinstallable validation entryを#445/#447で定義し、repository scriptをcopyしない |
| Selfrionette integration diagnostic | `run_fast_arm_endpoint_motion_sanity.py`、`run_fast_arm_jacobian_mobility_diagnostics.py`、`run_fast_arm_neutral_pose_evaluator.py`、`run_fast_arm_neutral_pose_startup_smoke.py`、`export_wasm_qpos_fixture.py` | `scripts/diagnostics/fast_arm/`候補 |
| viewer operation | `view_fast_arm_native_mujoco.py`、`run-browser-viewer-smoke.ps1`、`run_live_viewer_smoke.py` | `scripts/viewer/`候補 |
| repository operation | `plot_fast_arm_endpoint_trajectory_log.py` | `scripts/repository/`またはdiagnostic artifact tool。#448でconsumer確認 |
| hardware operation | fast_arm coreを直接importするものは現在なし。loadcell / serial scriptはhardware owner | `scripts/hardware/`。coreへ移さない |
| compatibility wrapper | `run_replay_mujoco_dry_run.py`、`run_replay_mujoco_websocket_publisher.py` | `scripts/compatibility/`。canonical `selfrionette` CLIを記載 |

本Issueではscriptを移動・変更しない。

## 10. Migration order

1. #445開始時にbaseline public exports、resource bytes/hash、Profile/Bundle/Runtime object identity、viewer declaration digest、
   FK/IK/site/limit/initial pose結果をfreezeする。
2. `core/pyproject.toml`と`core/src/fast_arm_core/`で独立Python package boundaryを成立させ、editable/install/wheelの
   import identityがすべて`fast_arm_core`であることを検証する。root projectへの導入方式は実測で選ぶ。
3. `fast_arm_core/definition.py`とpure `model_spec.py`を現行定数からmoveし、adapter旧moduleからre-exportする。値を再入力しない。
4. pure kinematicsとmodel-aligned kinematicsをcoreへmoveし、`adapter/kinematics.py`にgeneric Protocol/schema wrapperを
   置く。旧public solver classはadapter ownerの同一classをre-exportし、runtimeをそのclassへ接続する。
5. 現行MJCF `home`値を基準にinitial poseをcore definitionへmoveし、MJCF home、`InitialStateContract`、reference fixture、
   endpoint/orientation、viewer metadataをderived projectionとして完全一致させる。
6. `arm.xml`、mesh、joint-limit configをcore packageへmoveし、adapterの`scene.xml`からcore-owned `arm.xml`をincludeする。
   model load、XML include、model name、qpos、`tip` siteを不変にする。
7. viewer declarationとruntime-derived fixtureをadapter resourceへmoveし、public URL / VFS mapping / bytes / digestを維持する。
8. Profile、Runtime Plugin、Bundle、endpoint/model validator、diagnosticsをadapterへmoveする。
9. root `plugin.py`をadapter assemblyだけへ接続し、`ROBOT_PLUGIN`を唯一のdiscovery入口として再検証する。
10. 全consumerを新ownerまたは限定re-exportへ更新し、物理filesystem accessとしての旧resource path参照が0件であることを
   検査する。viewer JSON / payload / public URLのcompatibility identifierは旧文字列を維持してよい。
11. #446でtestをownership別に移す。#448でscriptを用途別に移す。#447のpreconditionが揃うまで外部化しない。

各step後もproduction entryを増やさず、current behaviorのtargeted testを通す。途中でadapterにduplicate定数を置かない。

## 11. Acceptance matrix

| validation | #445 in-repository split | #446 test ownership | #447 external core |
|---|---|---|---|
| package identity / import | editable/install/wheelで`fast_arm_core`、adapter import/API、`ROBOT_PLUGIN`単一入口。Selfrionette namespace core importなし | test import更新、generic owner維持 | directory外部化後も`fast_arm_core` API不変、未初期化fail |
| core dependency purity | `fast_arm_core`から`selfrionette`/runtime/CLI等のimport 0、runtime `sys.path`変更なし | architecture testをcore suiteへ配置 | core repository単体検査 |
| FK/IK | exact cases、seed/failure/tolerance | core testへ全case移動 | core単体 + adapter conformance |
| joint/motor conversion | 現行qpos/solver convention不変、未実装motor mappingを追加しない | convention test ownerを明示 | Python core/adapterの同じcontractを検証。multi-language parityは対象外 |
| joint limits | TOML bytes、parse、model validation、hold semantics | core parse / adapter guardへ分割 | core data + adapter behavior |
| initial pose | core definition -> XML `home` / contract / fixture / viewer metadata、qpos/tip/orientation/frameの完全一致 | core reference + integration continuity | pinned core revisionで同じprojectionを再現 |
| MuJoCo site consistency | model-aligned FK vs `tip`、frame/provenance | integrationへ移動 | adapter integrationで再検証 |
| resource ownership / integrity | core=`arm.xml`/mesh/config、adapter=`scene.xml`/viewer/fixture。XML include、model name、qpos、`tip`、STL hash/case、JSON/TOML decode | core/adapter resource tests | external core + adapter sceneのinclude/update/rollback |
| viewer VFS | public URL、VFS path/bytes、viewer declaration digest、WASM load | viewer generic test維持 | adapter配信で同一URL/bytes/digest |
| runtime/viewer/CLI | current targeted + full suite / viewer test/build | selection/coverage維持 | full suite / viewer build |
| clean clone / installed | wheel content、non-editable install、editable checkout | pytest selection | recursive setupまたはchosen distribution smoke |
| external revision pinning | 対象外。floating参照を導入しない | 対象外 | fixed revision、no runtime fetch、rollback、missing core fail-closed |

#445ではfull Python suite、architecture boundaries、viewer test/typecheck/build、clean wheel/install smokeを実行する。
#446はtest移動によるselection/coverage低下を検査する。#447はcore単体とSelfrionette adapterの両方をclean cloneから検証する。

## 12. Open decisions

### #445開始前に確定済み

- root `plugin.py::ROBOT_PLUGIN`だけがproduction discovery入口である。
- coreは当面Python-onlyで、公開package identityは`fast_arm_core`である。`core/`は将来の独立repository mount pointであり、
  Selfrionette namespace packageにしない。
- `fast_arm_core`はSelfrionetteをimportせず、adapterだけが両側を参照する。
- generic Protocol/schema/backend/runtime/viewerはfast_arm coreへ逆依存しない。
- `arm.xml`、mesh、config、pure kinematics、initial pose definitionはcore、`scene.xml`、Bundle/Profile/Runtime/provider/schema/viewer declarationはadapterである。
- initial pose definitionがSoTで、MJCF `home`、`InitialStateContract`、fixture、viewer metadataはprojectionである。
- runtime/MuJoCo/viewerをまたぐdiagnosticとfixtureはintegrationでありcoreではない。
- #445は独立package + package-local resourceをeditable/install/wheelで成立させ、pathだけを移して壊れたwheelを残さない。
- root projectのpath dependency / workspace / package discoveryの選択は#445の実装判断だが、package identityは変更しない。
- motor-space mappingはcurrent productionに存在しないため、#445は新規変換を設計・実装しない。現在のqpos/solver conventionだけを移す。
- #446までtest実体は移動せず、#448までscript実体は移動しない。
- #447まで外部repositoryやdistribution mechanismを導入しない。

### #447まで留保

- external repository名、visibility、owner、release / revision policy。
- submodule、pinned vendored snapshot、subtree、tagged archiveの選択。

### Python-only core運用後の別Issueへ留保

- Rust implementation / binary / static library / dynamic library、PyO3、maturin、C ABI、CXX。
- C++ implementation、openFrameworks integration、FastArmCommunicator変更。
- multi-language package設計、native binary distribution、Python/C++ parity test。
- physical motor-space / differential shoulder mapping。hardware characterizationと別behavior Issueが必要で、core分離だけから推論しない。

## Scope / impact

このinventoryは値、file配置、import、runtime、viewer、solver、payload、fixture、resource内容を変更しない。
今回と#445の当面のcore設計はPython-onlyであり、Rust、C++、openFrameworks、native binary、multi-language package、
motor-space mapping、physical differential shoulder mappingを実装しない。これらを#447の必須成果とも扱わない。
researchで実行・評価できる能力、実験条件、観測結果も変更しないためresearch logとexperiment noteは更新しない。
hardware validation、serial open、Arduino、OSC、実機操作、external repository作成、deployment、runtime network fetchは行わない。
