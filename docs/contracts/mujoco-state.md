---
status: canonical
owner: architecture
last_verified: 2026-11-11
canonical_for:
  - MuJoCoState contract
related:
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
---

# MuJoCoState契約

これはbackend-to-viewer state snapshotのcanonical contractである。

`MuJoCoState`はMuJoCo backendが生成するphysical snapshotである。
controller state、transport state、viewer stateではない。

## field

- `frame_index`: runtime/backendのframe counter。
- `time_s`: backend step後のMuJoCo `data.time`。
- `qpos`: model orderのMuJoCo `qpos`。
- `qvel`: model orderのMuJoCo `qvel`。
- `bodies`: MuJoCo model/dataから得たbody transform。
- `sites`: MuJoCo model/dataから得たsite transform。
- `target_position_m`: optionalなtarget marker feedback。diagnostic contextおよび
  viewer-facing presentation inputであり、physics stateまたはcommand-side
  desired endpoint stateではない。
- `metadata`: diagnosticまたはtransport helper data専用。source of truthではない。

## transform契約

- positionのunitはmeterである。
- quaternionは`wxyz` orderで保存する。
- bodyとsiteの名前は`docs/contracts/mujoco-model-name-contract.md`を正とする。
- viewer codeはこれらのtransformをread-only inputとして扱わなければならない。
- viewer codeは`target_position_m`をtarget markerとして表示してよいが、FK、IK、
  qpos pose recompute、physics stateとして再解釈してはならない。

## 注記

- `base_link`、`fore_arm_link`、`tip`はfast arm assetのcanonical model nameである。
- `frame_index`はbackend stepごとに1増加する。
- 次のsnapshotを構築する前にbackendで`mj_step`を実行する。
- backendは、後続の`apply_joint_position_command()`が上書きするまでtyped pending commandを保持する。
  また、snapshotをdirect qpos reflection contractと整合させるため、`mj_step`後に
  joint qposを再適用する。
- 他の文書ではfield ruleを再記載せず、この文書へlinkする。

## エンジン版と既知不具合の境界

現行のPython nativeとViewer WASMは4.0.0をlockで固定する。投機的接触は現行タスクでは使わない。
モデル/条件を記録する既存の`mujoco_version`は実行版を示し、同じモデルXMLでも異なる版の試行を
同一条件へ混合しない。nativeは唯一の物理状態の正本、WASMは描画専用という境界を維持する。

4.0.0の疎行列Newtonはupstream #3767のため未対応とする。共通loaderとFastArm providerの
初期化・resetで、`mj_isSparse`と実効solverを検査し、最初の`mj_forward`前に拒否する。
自由度数の独自判定、密行列/CGへのfallback、試行中のsolver変更で回避しない。
現行タスクは密行列であり、その数値条件は変えない。別engine版への移行には再検証が必要である。
判断根拠は[ADR 0016](../design/adr/0016-mujoco4-dense-migration.md)、観測値は
[移行検証記録](../experiment-notes/2026-11-11-mujoco4-migration.md)に分離する。
