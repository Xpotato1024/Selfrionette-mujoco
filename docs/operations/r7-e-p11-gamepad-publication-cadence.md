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

Issue #348 に対する draft implementation である。active な gamepad held state の publication cadence を backend liveness contract に合わせる。Ready、merge、Issue close は未承認である。

## Publication contract

- 初回 active sample と active state の変化は即時 publish する。
- unchanged active held state は `100 ms` cadence で publish する。
- zero、release、disconnect は即時 publish する。
- unchanged zero state は継続 publish しない。
- 実際の publication ごとに既存 sender の sequence を更新し、publication 時刻を timestamp に使う。
- heartbeat は active held state だけが所有し、同時に1本だけ存在する。

backend の liveness timeout `250 ms`、gamepad mapping、deadzone `0.1`、gain、axes/buttons、control frame、wire message shape は変更しない。heartbeat interval `100 ms` は timeout の半分 `125 ms` 以下である。

## Inactive lifecycle safety

gamepad の animation-frame polling は viewer の lifecycle とは独立して継続し得るため、publication controller に inactive state を持たせる。

- `blur` または `document.visibilityState !== "visible"` への遷移時は zero snapshot を即時 publish し、heartbeat を停止する。
- inactive 中の polling、`gamepadconnected`、`gamepaddisconnected`、その他の active sample は publication controller が無視する。
- visible になっただけでは再開しない。`document.visibilityState === "visible"` かつ `window` が focused の場合だけ resume する。
- resume 時は最新の `navigator.getGamepads()` を fresh sample として評価する。inactive 前に cached していた active snapshotをそのまま再送しない。
- resume 後の heartbeat は既存 controller が1本だけ再所有する。
- dispose 後は polling callback、publication、heartbeat のいずれも再開しない。

これにより、blur/hidden 時に一度 zero を送っても、継続中の polling が active state や heartbeat を復活させることはない。

## Socket lifecycle

React effect ごとに gamepad sender と publication controller を1つずつ生成する。effect cleanup では animation frame と publication controller の heartbeat を cancel した後、sender を dispose する。reconnect や unmount で旧 lifecycle が残らず、heartbeat loop が重複しない。socket unavailable や send failure は viewer を crash させない。

## Test matrix

- 初回、変更、unchanged held の immediate/heartbeat publication
- heartbeat publication ごとの sequence/timestamp 更新
- zero/release/disconnect の immediate publication と heartbeat 停止
- unchanged zero の抑制
- inactive 中の active polling sample の publication 抑制
- visible だけでは再開せず、visible+focused 復帰後の fresh sample だけで再開
- resume 後の heartbeat 1本所有
- dispose 後の publication/heartbeat 復活防止
- sender の schema、mapping、backend unavailable の既存回帰

timer test は injected deterministic timer を使用し、wall-clock sleep に依存しない。

## Lifecycle integration evidence

`apps/mujoco-viewer/tests/productViewerGamepadIntegration.test.ts` は、productionが利用する`gamepadLifecycle`結線に対してfake browserを注入する。windowの`blur`/`focus`、documentの`visibilitychange`と`hasFocus()`、animation-frame polling、`getGamepads()`のfresh sample、timerをdeterministicに制御し、active → inactive zero → polling抑制 → visibleだけでは待機 → focused resume → single heartbeat → dispose停止の状態遷移を検証する。

## Compatibility and scope

- backend Python / liveness timeout: 変更なし
- keyboard path: 変更なし
- transport schema / WebSocket message shape: 変更なし
- dependencies、package lock、CI: 変更なし
- runtime composition、MuJoCo、IK/FK、Three.js rendering: 変更なし
- serial、OSC、robot output、hardware validation: 実施しない

## Validation

- viewer `npm run typecheck`
- viewer `npm run build`
- viewer `npm test`
- Python viewer input-source / runtime step-loop compatibility tests
- `uv run pytest tests/architecture`
- `uv run python -m compileall src tests scripts`
- canonical root `uv run pytest`（P15 merge後のpytest discoveryで全件passを要求）
- `git diff --check`、UTF-8 without BOM、mojibake、PR metadata の確認

browser manual operation、browser backend server、external runtime server は起動しない。
