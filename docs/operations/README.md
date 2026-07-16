---
status: supporting
owner: architecture
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/README.md
---

# operations

反復利用する現在の操作手順と運用規則だけを置く。completion audit、inventory、Issue固有implementation evidenceは
`docs/reports/README.md`から辿る。

## repository運用

- `git-pr-workflow.md`: branch、diff、PR、head一致のgate
- `validation.md`: 変更層とfailure modeに応じたvalidation
- `codex-workflow.md`: Codex promptの共通ruleとtask-specific delta
- `japanese-doc-writing-guardrails.md`: UTF-8、BOM、mojibake、日本語方針
- `hardware-safety.md`: serial、OSC、hardware accessのoperator gate

## runtime / viewer起動と診断

- `runtime-dry-run.md`: deterministic replayからpayload v0 NDJSONまで
- `websocket-publisher-runner.md`: local/dev WebSocket publisher
- `websocket-host-port-contract.md`: bind hostとbrowser-visible hostの分離
- `backend-viewer-startup.md`: backend、publisher、viewerの起動入口
- `live-viewer-smoke.md`: live viewer smoke
- `runtime-to-viewer-e2e-smoke.md`: backendからbrowser viewerまでのE2E診断
- `browser-visual-smoke.md`: browser-visible scene smoke
- `mujoco-viewer-dev-launcher.md`: one-command / AutoPort / URL案内
- `product-viewer-wasm-scene-renderer.md`: product-owned WASM scene renderer
- `native-mujoco-fast-arm-viewer-check.md`: native MuJoCo fast_arm viewer check

## reusable test / manual procedure

- `generic-kinematics-test-doubles.md`: generic test-only FK/IK double
- `robot-runtime-plugin-conformance-tests.md`: Robot Runtime Plugin conformance suite
- `r6-l-keyboard-gamepad-live-viewer-smoke.md`: keyboard / gamepad live viewer manual smoke
- `r7-a-lite-serial-dry-run-smoke.md`: recorded fixtureによるserial dry-run
- `r7-b-manual-live-loadcell-runtime-runner.md`: operator-gated live loadcell runner
- `r7-c-viewer-fixture-demo-procedure.md`: viewer fixture demo
- `r7-c-keyboard-replay-demo-package.md`: keyboard / replay demo package
- `r7-c-live-loadcell-validation-log.md`: live loadcell validation procedure
- `r7-c-axis-sanity-check.md`: axis sanity protocol
- `r7-d-p3-fast-arm-endpoint-command-check-procedure.md`: no-hardware endpoint command smoke
- `r7-e-p1-fast-arm-endpoint-motion-sanity.md`: endpoint motion sanity gate

## historical path reference

次は特定実装時点のevidenceであり、current procedureとして実行しない。provenance維持のためpathだけを案内する。

- `r7-a-lite-websocket-viewer-smoke.md`: offline payload / viewer parser smoke evidence
- `r7-b-input-driven-websocket-viewer-smoke.md`: input-driven WebSocket / viewer smoke evidence
- `r7-c-manual-validation-preflight.md`: retired manual validation preflight
