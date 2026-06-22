---
status: canonical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C live loadcell validation log procedure
related:
  - docs/README.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md
  - docs/operations/r7-b-manual-live-loadcell-runtime-runner.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
---

# R7-C live loadcell validation log

## 目的

この文書は #235 の manual live loadcell validation log 手順を固定する。
live serial の実行は人間の operator が manual gate を確認した場合だけ行う。
Codex / CI は live serial、COM access、hardware validation、OSC、robot output を実行しない。

## manual command example

人間が実行する場合だけ、repo root から次の形で実行する。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
uv run python scripts/run_live_loadcell_runtime.py --port COM5 --baud-rate 115200 --max-frames 120
```

`--port` は実環境に合わせて operator が明示する。
自動 COM detection は行わない。
`--max-frames` は finite にする。

## operator checklist

実行前に次を確認する。

- R7-C preflight と keyboard / replay demo package を読み終えている
- 実行者が port、baud rate、max frames を明示している
- robot output、actuator command、OSC send が無効である
- firmware upload / modification を行わない
- browser / WebSocket server をこの手順では起動しない
- emergency stop / cable disconnect など人間側の停止手段を確認している
- log 保存先と file name を決めている
- pyserial unavailable の場合は live mode を停止し、fixture / no-hardware path に戻る

## expected startup banner

startup banner には少なくとも次が出ることを期待する。

```text
manual gated live serial mode
port=<operator-selected-port> baud_rate=<operator-selected-baud-rate> max_frames=<finite-frame-count>
```

banner が port / baud rate / max frames を示さない場合は validation を開始しない。

## 記録項目

記録は [r7-c-live-loadcell-validation-template.md](../experiment-notes/templates/r7-c-live-loadcell-validation-template.md)
を複製して行う。

必須記録欄:

- operator
- date / local time
- branch / commit
- port
- baud rate
- max frames
- observed frame count
- startup banner observed
- pyserial availability
- desired_endpoint_m observed
- payload metadata observed
- no OSC / no robot output safety confirmation
- failure / anomaly notes
- stop reason

## desired_endpoint_m / payload metadata confirmation

確認対象は simulation-facing payload metadata である。

- `metadata["desired_endpoint_m"]` が存在する
- `metadata["source_kind"]` が `loadcell_serial` である
- `metadata["frame_index"]` が observed frame count と矛盾しない
- `metadata["serial_timestamp_s"]` が記録できる
- `metadata["serial_port"]` / `metadata["baud_rate"]` が live mode で記録される
- `target_position_m` は primary command ではない

## failure / anomaly handling

次の場合は caution または fail として記録する。

- startup banner が期待項目を欠く
- observed frame count が 0
- `desired_endpoint_m` が欠ける
- payload metadata が読めない
- pyserial unavailable
- serial framing error が連続する
- unexpected port / baud rate が表示される
- OSC、robot output、actuator command の可能性が見えた

## safety confirmation

この手順で許可されるのは loadcell serial input の manual observation だけである。

- OSC sent: no
- robot output: no
- actuator command: no
- firmware upload: no
- firmware modified: no
- browser E2E: no
- WebSocket server: no
- hardware validation by Codex / CI: no

## Codex / CI boundary

Codex / CI はこの live serial command を実行しない。
CI で行うのは docs-only validation と template presence の確認だけである。
live serial の結果は人間が template に記録し、必要に応じて後続 issue で読む。

## handoff

次は #236 で axis sanity check protocol を追加する。
この log template の observed / expected 欄は
`docs/operations/r7-c-axis-sanity-check.md` の keyboard / replay / live loadcell observation と接続する。

## Scope Check

```text
legacy changed: no
legacy imported/executed: no
assets changed: no
schema breaking change: no
import boundary changed: no
MuJoCo package imported: no
MuJoCo model load included: no
MuJoCo forward included: no
MuJoCo step included: no
MuJoCoState snapshot included: no
runtime composition included: no
Three.js FK/IK included: no
WebSocket included: no
serial port opened by Codex/CI: no
OSC sent: no
hardware validation included by Codex/CI: no
node_modules included: no
dist included: no
.env.local included: no
docs / SoT impact checked: yes
```
