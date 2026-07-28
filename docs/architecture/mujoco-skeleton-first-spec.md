---
status: canonical
owner: architecture
last_verified: 2026-07-28
canonical_for:
  - MuJoCo skeleton and layer ownership
related:
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# MuJoCo skeleton-first仕様

## source of truth

MuJoCo modelとbackend stateがphysical stateのsource of truthである。Three.js viewerは受信したstateを描画する
rendering-only consumerであり、独立したFK / IK、physics step、qpos再計算を持たない。

schemaはlayer間contractである。複数layerの接続、lifecycle、failure propagationは`runtime/`が所有する。
`legacy/`はhistorical evidenceであり、明示scopeなしにcurrent implementationからimportまたは実行しない。

## layer ownership

| layer | 現在の責務 | 禁止事項 |
| --- | --- | --- |
| `schemas/` | immutableなlayer contract | runtime composition、I/O |
| `plugins/input_sources/` | operator / replay / viewer inputの取得 | mapping、motion生成、backend更新 |
| `plugins/mappings/` | raw inputから`InputIntent`への変換 | device I/O、qpos更新 |
| `motion/` | intentからcommandを生成 | MuJoCo stateの直接変更 |
| `kinematics/` | robot pluginが選ぶFK / IK | viewerへのsolver複製 |
| `mujoco_backend/` | model load、forward / step、state measurement | UI所有 |
| `transport/` | stateのserialize / delivery | physics計算、state再解釈 |
| `runtime/` | 唯一のmulti-layer composition root | layer contractの暗黙な破壊 |
| `apps/mujoco-viewer/` | payloadのrenderingとoperator input送信 |第二のphysical state SoT |

## stub / negative-control boundary

NoOp、zero、static implementationは、unit test、negative control、明示的なwiring確認に限定する。
production compositionはselected `RobotRuntimePlugin`が提供するconcrete implementationを解決し、
zero-valued FK / IK、generic Planar solver、NoOp motionへ暗黙fallbackしない。unsupported configurationは
明示的に失敗させる。

pre-audit導入順とimplementation evidenceは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
