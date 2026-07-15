---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C presentation-ready demo notes
related:
  - docs/README.md
  - docs/operations/r7-c-viewer-fixture-demo-procedure.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/operations/r7-c-live-loadcell-validation-log.md
  - docs/operations/r7-c-axis-sanity-check.md
  - docs/operations/hardware-safety.md
---

# R7-C presentation demo notes

## 目的

この文書は #237 の presentation-ready demo notes を固定する。
中間発表で説明する demo narrative、proven / intentionally unproven、
fallback demo plan、known risks を 1 か所にまとめる。

この文書は docs-only であり、Codex / CI は browser、WebSocket server、
serial、COM、hardware、OSC、robot output を実行しない。

## demo narrative

R7-C の demo は、実機制御ではなく simulation-facing pipeline を安全に説明する。

```text
keyboard / replay / manual loadcell observation
-> desired_endpoint_m
-> payload v0 / endpoint_evaluation
-> viewer read-only overlay
-> presentation explanation
```

説明の中心は、入力が command-side `desired_endpoint_m` として揃い、
viewer は rendering-only / read-only に表示する、という境界である。

## what is proven

- R7-C preflight と safety boundary を事前確認できる
- viewer launch / fixture demo procedure を人間が追える
- keyboard / replay demo package で no-hardware path を説明できる
- `desired_endpoint_m` は command-side endpoint として読む
- `target_position_m` は primary command ではなく viewer feedback / compatibility field として読む
- `endpoint_evaluation` は read-only diagnostic overlay として説明できる
- live loadcell validation は manual-gated log template に記録する形で扱える
- axis sanity check は pass / caution / fail として発表前に整理できる

## what is intentionally unproven

- real robot output
- actuator command
- OSC send
- firmware upload / modification
- physical axis finalization
- force unit calibration
- final loadcell-to-axis mapping
- browser E2E automation by Codex / CI
- WebSocket server execution by Codex / CI
- live serial / COM execution by Codex / CI
- hardware validation by Codex / CI

## viewer / payload / input pipeline

### input

- keyboard は no-hardware contract smoke として説明する
- replay は deterministic `sweep_x` fixture として説明する
- live loadcell は human-run observation log として説明する

### payload

- payload v0 を viewer-facing transport contract として説明する
- `metadata["desired_endpoint_m"]` を command-side endpoint として説明する
- `target_position_m` は viewer feedback / compatibility field に留める
- `endpoint_evaluation` は optional diagnostic であり、control truth source ではない

### viewer

- viewer は rendering-only である
- viewer-side FK / IK / qpos recompute はしない
- `Endpoint evaluation: unavailable` は optional diagnostic 欠落時の正常表示である
- marker / overlay は payload を読むための presentation aid であり、物理 SoT ではない

## demo flow

1. R7-C preflight と safety exclusions を説明する
2. viewer launch procedure の URL / WebSocket URL の違いを説明する
3. replay fixture demo と `sweep_x` payload の見方を説明する
4. keyboard demo package で `desired_endpoint_m` の生成を説明する
5. live loadcell は manual-gated template で記録することを説明する
6. axis sanity check の pass / caution / fail を説明する
7. intentionally unproven と next phase を明示する

## fallback demo plan

browser / WebSocket / live serial が当日使えない場合は、次の fallback に切り替える。

- no-hardware docs walkthrough
- recorded payload / log の読み上げ
- `desired_endpoint_m` / `target_position_m` / `endpoint_evaluation` の field explanation
- #235 template と #236 axis sanity template の blank form walkthrough
- R7-B completion audit の proven / unproven 境界説明

fallback でも real robot output、OSC、actuator command は扱わない。

## known risks and mitigation

| Risk | Mitigation |
|---|---|
| browser / WebSocket server が当日使えない | fallback demo plan に切り替える |
| live loadcell serial が使えない | #235 template に pyserial unavailable / no live run と記録する |
| axis sign が直感と違う | #236 で caution / fail として記録し、final mapping と主張しない |
| `target_position_m` を primary command と誤解する | `desired_endpoint_m` が command-side endpoint であると説明する |
| endpoint evaluation が欠ける | optional diagnostic として説明し、viewer failure と扱わない |

## no robot output / no OSC safety statement

R7-C presentation demo は実機制御ではない。

- OSC sent: no
- real robot output: no
- actuator command: no
- firmware upload: no
- firmware modified: no
- hardware validation by Codex / CI: no
- serial / COM by Codex / CI: no
- browser E2E by Codex / CI: no
- WebSocket server by Codex / CI: no

## handoff

次は #238 で R7-C completion audit を追加する。
この demo notes は `docs/operations/r7-c-completion-audit.md` で parent #231 close-readiness を判断する材料にする。

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported by PR: no
MuJoCo model load included by PR: no
MuJoCo forward included by PR: no
MuJoCo step included by PR: no
MuJoCoState snapshot included by PR: no
runtime composition included by PR: no
Three.js FK/IK included: no
WebSocket included by Codex/CI: no
serial port opened by Codex/CI: no
OSC sent: no
hardware validation included by Codex/CI: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
