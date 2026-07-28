---
status: canonical
owner: operations
last_verified: 2026-07-29
canonical_for:
  - R7-C live Selfrionette validation log procedure
related:
  - docs/README.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/experiment-notes/templates/r7-c-live-loadcell-validation-template.md
  - docs/operations/r7-b-manual-live-selfrionette-runtime-runner.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
---

# R7-C live Selfrionette validation log

## 目的

この文書は`selfrionette/v1`のmanual live serial validation手順を固定する。
Selfrionetteはdevice / Input Source identity、loadcellはdevice内のsensor / sample semantics、
serialはacquisition backendである。

Codex / CIはlive serial、COM access、hardware validation、OSC、robot outputを実行しない。
実行と観測はhardware safety gateを確認した人間のoperatorだけが行う。

## manual command example

```powershell
uv run python scripts/hardware/selfrionette/run_live_selfrionette_runtime.py `
  --port COM5 `
  --baud-rate 115200 `
  --max-frames 120
```

自動COM detectionは行わない。`--port`はoperatorが明示し、`--max-frames`は有限値にする。

## operator checklist

- R7-C preflightとkeyboard / replay demo packageを確認した。
- port、baud rate、max framesをoperatorが明示した。
- robot output、actuator command、OSC sendは無効である。
- firmware upload / modificationを行わない。
- browser / WebSocket serverをこの手順では起動しない。
- 人間側の停止手段とlog保存先を確認した。
- `pyserial`がない場合はlive backendを開始せず、injected-lines pathへ戻る。

## expected startup banner

```text
manual gated live Selfrionette serial mode
port=<operator-selected-port> baud_rate=<operator-selected-baud-rate> max_frames=<finite-frame-count>
```

bannerに対象port、baud rate、max framesがない場合はvalidationを開始しない。

## 記録項目

記録にはhistorical evidence template
[r7-c-live-loadcell-validation-template.md](../experiment-notes/templates/r7-c-live-loadcell-validation-template.md)
を使用する。このtemplate名の`loadcell`は過去Roundのevidence identityとして保持しており、
current production Input Source identityではない。

- operator
- date / local time
- branch / commit
- port / baud rate / max frames
- observed frame count
- startup banner observed
- pyserial availability
- `desired_endpoint_m` observed
- payload metadata observed
- no OSC / no robot output safety confirmation
- failure / anomaly notes
- stop reason

## payload confirmation

- `metadata["source_kind"] == "selfrionette"`
- `metadata["desired_endpoint_m"]`が存在する
- `metadata["frame_index"]`がobserved frame countと矛盾しない
- `metadata["serial_timestamp_s"]`を記録できる
- live backendでは`metadata["serial_port"]` / `metadata["baud_rate"]`を記録する
- `target_position_m`をprimary commandとして扱わない

## failure handling

次の場合はcautionまたはfailとして記録し、acquisitionを停止する。

- startup bannerが期待項目を欠く
- observed frame countが0
- `desired_endpoint_m`または必要なpayload metadataを欠く
- serial framing errorが継続する
- unexpected port / baud rateが表示される
- OSC、robot output、actuator commandの可能性が見える

`pyserial` unavailableのactual errorは次である。

```text
serial module is required for live Selfrionette mode. Install pyserial or use injected lines.
```

## safety confirmation

- OSC sent: no
- robot output: no
- actuator command: no
- firmware upload / modification: no
- browser E2E / WebSocket server: no
- hardware validation by Codex / CI: no
