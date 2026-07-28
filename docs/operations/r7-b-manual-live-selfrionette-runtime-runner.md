---
status: canonical
owner: operations
last_verified: 2026-07-29
canonical_for:
  - R7-B-P5 manual live Selfrionette runtime runner
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
---

# R7-B-P5 manual live Selfrionette runtime runner

## 目的と用語

この手順は、`selfrionette/v1` Input Sourceをsimulation runtime pipelineへ接続する
operator-gated entry pointを定義する。

- Selfrionette: device / Input Source identity
- loadcell: Selfrionetteが使用するphysical sensorと7 channel sample
- serial / injected lines: acquisition backend

`loadcell_serial`をlogical source identityとして使用しない。runtime APIは
`LiveSelfrionetteRuntimeRunnerConfig`と
`run_live_selfrionette_runtime_runner()`を正本とする。

```text
Selfrionette serial or injected lines
-> Selfrionette reader / parser
-> loadcell_vector_sample/v1
-> loadcell_normalized_input_intent/v1
-> MotionCommand.metadata["desired_endpoint_m"]
-> runtime stepping
-> payload v0
```

## 安全境界

- `--port`はlive serial backendで必須とする。
- `--max-frames`は有限値とする。
- import、plugin discovery、catalog、factory constructionではserial portを開かない。
- acquisitionは明示的な`start()`後にだけ開始する。
- CI / testsはserial、COM、hardwareへ接続しない。
- firmware upload、OSC、robot / actuator output、deploymentは行わない。
- browser / WebSocket serverはこのentry pointから起動しない。

## current command

人間のoperatorがhardware safety gateを確認した場合だけ実行する。

```powershell
uv run python scripts/hardware/selfrionette/run_live_selfrionette_runtime.py `
  --port COM5 `
  --baud-rate 115200 `
  --max-frames 120
```

hardwareを使わないinjected-lines確認ではfixtureを指定する。

```powershell
uv run python scripts/hardware/selfrionette/run_live_selfrionette_runtime.py `
  --fixture tests/fixtures/r7_a_lite_serial_frames/minimal_valid.txt `
  --max-frames 1
```

fixture modeはserial portを開かない。startup bannerは
`manual gated Selfrionette fixture mode: serial is not opened`を表示する。
live modeは`manual gated live Selfrionette serial mode`とoperator-selected
`port` / `baud_rate` / `max_frames`を表示する。

## runtime contract

runnerはsource selectionを`selfrionette/v1`として解決し、Mappingを独立に選択する。
default convenience policyはruntime compositionが所有し、Input Source packageは具体Mapping IDを
所有しない。source/mapping schema compatibilityはsourceの`start()`前に検証する。

出力metadataでは次を確認する。

- `source_kind=selfrionette`
- `desired_endpoint_m`はcommand-side metadata
- `target_position_m`はprimary commandではない
- live backendでは`serial_port`と`baud_rate`を記録する
- `frame_index`と`serial_timestamp_s`を記録する

## troubleshooting

live backendで`pyserial`をimportできない場合は、次のactual errorでfail closedする。

```text
serial module is required for live Selfrionette mode. Install pyserial or use injected lines.
```

この場合はlive acquisitionを開始せず、injected-lines / fixture modeを使用する。
