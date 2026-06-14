---
status: canonical
owner: architecture
last_verified: 2026-06-15
canonical_for:
  - R6-F-P4 DoF ring reference audit
related:
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
  - apps/mujoco-viewer/README.md
---

# R6-F-P4 DoF Ring Reference Audit

R6-F-P4 は旧 Selfrionette Web View の DoF ring 表示を reference として確認し、`apps/mujoco-viewer/` に最小の presentation skeleton を追加する issue である。

この文書は audit と boundary freeze だけを目的とする。旧実装の直接移植、legacy import、legacy execute、UI parity 再現は行わない。

## 参照した legacy の材料

checked-in legacy tree では browser-side の DoF ring renderer そのものは見つからなかったため、近い参照として次を確認した。

- `legacy/fast_arm_control/gui_controller.py`
- `legacy/fast_arm_control/ik_controller.py`
- `legacy/fast_arm_control/mujoco_sim/run.py`

これらは joint 表示、IK、OSC、MuJoCo control が一体化した旧系統の実装であり、viewer-side の presentation skeleton をそのまま移植する材料にはならない。

## 取り入れる要素

- DoF ring を表示要素として扱うこと
- ring を read-only の presentation object として扱うこと
- ring の metadata に `id`、logical joint label、presentation role、visibility / availability status を持たせること
- ring の placement を payload 由来の body transform に従わせること
- browser-visible smoke で DoF ring の存在を観測できること
- marker / arm skeleton / fast_arm mesh と衝突しない別系統の scene object として扱うこと

## 取り入れない要素

- legacy の import / execute
- FK / IK / qpos pose recompute
- viewer-side target delta 解釈
- physics / command / backend source of truth 化
- old Web View の UI parity 再現
- joint angle を ring から生成する実装
- rendered arm mesh の新規設計
- browser-side MuJoCo model loading

## 直接移植しない理由

旧系統の joint UI は、表示と IK / OSC / controller が密結合していた。そのまま持ち込むと、DoF ring が command boundary や kinematics の源泉として誤解される。

この issue では ring を `payload -> viewer presentation` の read-only overlay に落とし、source of truth を MuJoCo backend 側に残す。

## MuJoCo Viewer での最小方針

- ring は presentation object とする
- ring の pose は payload 由来の body transform に従う
- ring は `qpos` から再計算しない
- ring は FK / IK で補完しない
- ring は `base_link_to_tip` fallback line skeleton とは別物として扱う
- ring は fast_arm mesh と同じ scene 上に載るが、役割は overlay である

## #91 との違い

- #90 は DoF ring に限定する
- #91 は旧 Web View の有用表示要素全体を audit する
- #90 は最小表示 skeleton と reference audit を先に固める
- #91 はその後に broader な表示要素の棚卸しを行う

## 結論

- DoF ring は表示責務である
- DoF ring は source of truth ではない
- viewer-side FK / IK / qpos pose recompute はしない
- legacy import / execute / direct migration はしない
- browser-visible smoke では ring の存在だけを確認する
