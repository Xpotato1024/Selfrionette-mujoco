---
status: draft
owner: viewer
last_verified: 2026-07-10
canonical_for:
  - R7-E follow-up P11 gamepad publication cadence
related:
  - docs/operations/r7-e-p8-architecture-endpoint-audit.md
  - docs/architecture/runtime-composition.md
---

# R7-E follow-up P11 gamepad publication cadence

## Status

Issue #348 の draft implementation である。active non-zero gamepad held state の
publication cadence を backend liveness contract に合わせる。Ready、merge、Issue close は
未承認である。

## Numbering / SoT

- Numbering SoT: #293
- Parent: #324
- Round: R7-E follow-up Batch 1
- Slot: P11
- Issue: #348
- P8 evidence: #343 / PR #344
- P16 handoff: #353

## Problem

browser は animation frame ごとに gamepad snapshot を取得していたが、値が変化しない
snapshot の publication を抑止していた。一方、backend の
`DEFAULT_VIEWER_INPUT_COMMAND_TIMEOUT_MS` は `250 ms` である。そのため、analog input を
保持していても最後の message から `250 ms` を超えると stale / hold になり得た。

## Frontend Publication Contract

- 初回 snapshot と変更 snapshot は直ちに publish する。
- active non-zero held state は値が変化しなくても heartbeat で publish する。
- zero / release / disconnect transition は直ちに publish する。
- unchanged zero state は継続 publish しない。
- publication ごとに既存 sender が sequence を増加し、publication 時刻を timestamp に使う。
- gamepad mapping、deadzone、gain、control frame、message shape は変更しない。

## Backend Liveness Contract

backend liveness threshold は `250 ms` のまま変更しない。frontend の heartbeat interval は
threshold の半分以下とし、active held message が値の不変だけを理由に stale にならない
ようにする。backend Python、runtime safety、hold behavior は本変更の対象外である。

## Heartbeat Interval

heartbeat interval は `100 ms` とする。`250 ms / 2 = 125 ms` 以下であり、通常の timer
dispatch jitter に対する余裕を持たせる。fixture の exact decimal へ合わせた値ではない。
browser が OS や page lifecycle により timer を停止または大幅に throttle する場合まで
liveness を保証するものではない。

## Change / Hold / Release / Disconnect Behavior

| State | Publication |
|---|---|
| first active sample | immediate |
| changed active sample | immediate; heartbeat timer を再開 |
| unchanged active held sample | `100 ms` heartbeat |
| zero / release transition | immediate; heartbeat 停止 |
| unchanged zero state | suppressed |
| disconnect transition | immediate zero snapshot; heartbeat 停止 |

release と disconnect は heartbeat を待たない。active held heartbeat は input を再解釈せず、
最新の normalized snapshot を同じ wire shape で再送する。

## Socket Lifecycle

React effect ごとに既存 gamepad sender を一つだけ生成し、publication controller も一つだけ
生成する。controller は active state に対して timeout を一つだけ所有する。変更時は既存
timeout を cancel して再設定し、dispose / unmount では timeout と animation frame を
cancel した後に sender を dispose する。connection state の再接続で旧 effect が cleanup
されるため、heartbeat loop は重複しない。backend が unavailable でも sender は例外を
viewer へ伝播しない。

## Compatibility

- source kind: unchanged
- message shape: unchanged
- axes / buttons: unchanged
- deadzone: `0.1` unchanged
- gain / local endpoint speed: unchanged
- control frame: `world` unchanged
- keyboard path: unchanged
- backend threshold: `250 ms` unchanged
- transport protocol: unchanged
- dependency: added none

## Test Matrix

- first / changed active sample の即時 publication
- unchanged active state の `100 ms` heartbeat
- heartbeat ごとの sequence 増加と timestamp 更新
- zero / release / disconnect の即時 publication と timer 停止
- unchanged zero suppression
- dispose / reconnect 時の単一 timer ownership
- backend unavailable 時の no-crash
- existing mapping / schema fixture の維持

timer test は injected deterministic timer を使い、wall-clock sleep や browser manual operation
に依存しない。

## Limitations

background page や OS が JavaScript timer を停止する状態は browser lifecycle の外部条件で
あり、本契約の `100 ms` cadence では保証しない。live browser / physical gamepad smoke は
実施していない。backend timeout の変更や general scheduling framework は導入しない。

## Handoff to P16

P16 / #353 は keyboard、gamepad、Selfrionette の evaluation-ready input API を扱う。本変更は
gamepad held-state liveness のみを固定し、mapping、normalization、deadzone、gain、frame の
統合設計を先取りしない。

## Validation

- viewer typecheck / build / tests
- viewer input-source と runtime step-loop の Python compatibility tests
- architecture tests
- Python compileall
- full pytest（P15前は既知の legacy collection failure を別記）
- diff / UTF-8 without BOM / mojibake check

browser backend server と external runtime server は起動しない。browser manual operation は
validation pass として扱わない。

## Hardware / External Effects

- serial port opened: no
- Arduino upload: no
- OSC sent: no
- robot output: no
- hardware validation: not run
- Selfrionette hardware accessed: no
- runtime external network side effect: no
- browser backend server launched: no

GitHub Issue / PR operations のみ、明示された範囲で実施する。
