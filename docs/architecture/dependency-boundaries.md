---
status: canonical
owner: architecture
last_verified: 2026-07-17
canonical_for:
  - import boundaries
related:
  - tests/architecture/test_import_boundaries.py
---

# dependency境界

この文書はimport境界だけを定義する。data flow、runtime composition、
viewer/transport contractはarchitecture文書とcontract文書で定義し、importから推測しない。

許可するdependency方向:

```text
schemas
  -> input_sources
input_interpreters
kinematics
motion
mujoco_backend
transport
  -> runtime
```

許可する例:

```text
input_sources       -> schemas
input_interpreters  -> schemas
motion              -> schemas, kinematics
kinematics          -> schemas
mujoco_backend      -> schemas
transport           -> schemas
runtime             -> all layers
```

Robot plugin compositionでは、上記layer境界に加えて次の方向を固定する。

```text
generic schema / domain / Protocol
  <- generic registry / provider adapter / Robot Bundle contract
  <- robot-specific profile / runtime / feasibility / initial state
  <- Robot Bundle assembly
  <- robot-specific plugin.py / ROBOT_PLUGIN registration
  <- bounded first-party discovery / plugins/catalog.py
  <- application composition root
```

- `selfrionette.plugins.robot_discovery`は`selfrionette.plugins.robots`直下packageだけを列挙し、
  固定`plugin.py`の固定`ROBOT_PLUGIN`だけを読む。configuration値、robot ID、external entry pointを
  import pathとして使用しない。
- 各robot packageの`ROBOT_PLUGIN`はBundle、viewer declaration、resource declaration、
  onboarding contract versionを一つのimmutable registrationへ束ねる。`__init__.py`の
  import副作用で自己登録しない。onboarding contract versionはregistration schema軸であり、
  Bundle / Profile / Viewerのrobot logical version軸とは独立させる。
- `selfrionette.plugins.catalog`はproduction discovery結果の唯一のprojection入口であり、
  concrete robot package、具体robot ID、Bundle singletonを直接importまたは列挙しない。
- ProfileとRuntime Pluginのresolverは、別registryへ具体objectを重複登録せず、resolved Bundleの
  `profile`と`runtime_plugin`を返す。
- generic `runtime` contract、`kinematics`、`motion`、generic MuJoCo backendは
  `selfrionette.plugins`、catalog、Bundle assembly、evaluation manifestへ逆依存しない。
- application compositionはcatalogからBundleをresolveし、consumerへ必要なtyped providerだけを渡す。
- `robots/fast_arm.py`、旧`runtime/fast_arm_*.py`、旧registry moduleはcompatibility facadeであり、
  新規consumerのcomposition APIとして使用しない。
- package root `selfrionette.runtime`はpublic compatibility surfaceをlazy resolveするが、package importだけで
  concrete catalogをloadしない。
- production discoveryを起動できるgeneric moduleはcatalogだけとする。test fixtureはproduction namespaceへ
  置かず、明示的なtest discovery rootを使用する。
- registration resourceは宣言identityと同じ`assets/mujoco/<robot_id>/` / `configs/<robot_id>/`へ限定し、
  viewer public URLは検証済みasset pathからdeterministicに生成する。shared resourceは暗黙許可しない。

禁止するdependency:

```text
input_sources       -> motion
input_sources       -> kinematics
input_sources       -> mujoco_backend
input_sources       -> transport
input_sources       -> runtime

input_interpreters  -> input_sources
input_interpreters  -> motion
input_interpreters  -> kinematics
input_interpreters  -> mujoco_backend
input_interpreters  -> transport
input_interpreters  -> runtime

motion              -> input_sources
motion              -> input_interpreters
motion              -> mujoco_backend
motion              -> transport
motion              -> runtime

kinematics          -> input_sources
kinematics          -> input_interpreters
kinematics          -> mujoco_backend
kinematics          -> transport
kinematics          -> runtime

mujoco_backend      -> input_sources
mujoco_backend      -> input_interpreters
mujoco_backend      -> motion
mujoco_backend      -> transport
mujoco_backend      -> runtime

transport           -> input_sources
transport           -> input_interpreters
transport           -> motion
transport           -> kinematics
transport           -> mujoco_backend
transport           -> runtime
```

これらの境界を変更する場合は、この文書、import boundary test、PRのArchitecture Impactを
同じ変更で更新する。

`apps/mujoco-viewer/src`は`tests/architecture/test_layer_import_boundaries.py`で
検査する。rendering-onlyを維持し、MuJoCo、IK/FK、Rapier layerをimportしてはならない。

## legacy参照と移行境界

`legacy/`は参照専用であり、新しい実装から直接importまたはexecuteしない。
legacyの責務を移行する場合は、script全体をcopyせず、次のownerへ責務単位で移す。

| legacyの責務 | current owner | 境界 |
|---|---|---|
| MuJoCo XML / STL asset | `assets/mujoco/fast_arm/` | canonical assetを参照し、legacy codeを実行しない |
| device input読取 | `input_sources/` | `RawInputFrame`を返し、IKまたはMuJoCo stateを書き換えない |
| inputの意味付けとscale | `input_interpreters/` | `RawInputFrame`を`InputIntent`へ変換する |
| target更新とsafety limit | `motion/` | `MotionCommand`を生成する |
| FK / IK / joint limit | `kinematics/`またはrobot-specific plugin | kinematics責務に限定する |
| MJCF model state | `mujoco_backend/` | MuJoCoをphysical stateのsource of truthとする |
| logging / replay / WebSocket delivery | `transport/` | motionまたはkinematics logicを所有しない |
| application composition | `runtime/` | 唯一のcomposition rootとする |
| visual rendering | `apps/mujoco-viewer/` | Three.js rendering-onlyとする |

## public export境界

package-root exportとmodule-level exportは別のpublic surfaceである。

- package-root `__all__`へ公開するのはcontract、concrete implementation、または
  canonical文書で維持理由を説明できるcompatibility helperに限定する。
- `selfrionette.runtime`は各public nameをowner moduleとattribute nameの明示mappingで解決する。
  module scan、transitive import、module orderingへ解決先を依存させない。generic contractの参照では
  concrete catalogをloadせず、catalog-backed resolverを参照した時点だけcompatibility facade経由でloadする。
- 明示mappingのkey setは`__all__`と一致させ、全entryのowner object identityをarchitecture testで固定する。
- `NoOp*`、`Zero*`、`Static*`などのstub classをpackage-rootのstable APIにしない。
- `stubs.py`はexplicit import用namespaceとして維持し、stubを使用するcallerは
  `.stubs`から明示的にimportする。
- `stubs.py.__all__`にはstub classだけを含め、contract re-exportを含めない。
  contractがmodule attributeとしてexplicit import可能であることとは区別する。
- production default、concrete runtime、replay runtime、publisher runnerは
  `.stubs`を直接importしない。compatibility helperからの利用は明示的なallowlistに限定する。

このpublic surfaceを変更する場合は、`tests/architecture/test_public_export_policy.py`と
該当packageの`__all__` assertionを同じ変更で更新する。
