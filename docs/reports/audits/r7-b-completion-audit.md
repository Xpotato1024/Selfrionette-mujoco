---
status: historical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-B completion audit
related:
  - docs/README.md
  - docs/contracts/r7-b-runtime-input-pipeline-contract.md
  - docs/operations/r7-b-input-driven-websocket-viewer-smoke.md
  - docs/operations/r7-b-manual-live-loadcell-runtime-runner.md
  - docs/operations/r7-a-lite-completion-audit.md
  - docs/operations/r7-a-lite-serial-dry-run-smoke.md
  - docs/operations/r7-a-lite-websocket-viewer-smoke.md
  - docs/operations/validation.md
  - docs/operations/hardware-safety.md
---

# R7-B Completion Audit

## Scope

R7-B の simulation-facing input pipeline について、`#217` から `#223` までの完了範囲、未完了範囲、明示的に未証明の境界を docs に固定する。

この audit は docs / audit only であり、新規 runtime 実装、viewer 実装、serial 実行、hardware validation は行わない。

## Completed Issues

| Issue | PR | Status | Notes |
|---|---|---|---|
| `#217` runtime input pipeline contract | `#224` | merged | runtime input pipeline contract を固定済み |
| `#218` MotionCommand desired_endpoint_m resolver | `#225` | merged | command-side endpoint resolver を追加済み |
| `#219` keyboard / replay input source smoke | `#226` | merged | keyboard / replay の smoke を追加済み |
| `#220` offline InputSource -> MuJoCo runtime stepping smoke | `#227` | merged | offline stepping smoke を追加済み |
| `#221` input-driven WebSocket / viewer smoke | `#228` | merged | input-driven payload の read-only parse smoke を追加済み |
| `#222` manual-gated live loadcell serial runtime runner | `#229` | merged | manual-gated live runner を追加済み |
| `#223` completion audit | current audit / draft PR | pending | この文書 |

## Proven

- `desired_endpoint_m` は command-side endpoint として resolver で解決できる。
- `target_position_m` は primary command ではなく viewer feedback / fallback である。
- keyboard input は WASD + Space / Shift default keybind で `desired_endpoint_m` を生成できる。
- keybind config reserved path は `configs/input/keyboard_default.json` である。
- replay fixture は `desired_endpoint_m` を持つ `MotionCommand` に変換できる。
- keyboard / replay command は offline MuJoCo runtime stepping smoke に入る。
- offline runtime stepping result は payload v0 に変換できる。
- viewer parser は input-driven payload を read-only に parse できる。
- `endpoint_evaluation` は optional diagnostic として扱える。
- live loadcell serial runner は manual-gated である。
- `--port` 明示時のみ live path に入る。
- tests / CI は serial / COM / hardware / OSC / browser / WebSocket server を開かない。

## Intentionally Unproven

- 実機 loadcell live serial validation
- COM5 等の実ポート open
- pyserial installed live mode 実行
- WebSocket server 実起動
- browser viewer 実起動
- browser E2E
- OSC send
- real robot output
- actuator command
- firmware upload / modification
- physical axis finalization
- force unit calibration
- robotics-grade IK / FK redesign

## Safety / Access Confirmation

`#217` から `#222` の流れとして、以下は行っていない。

- serial port open: not performed in tests
- COM access: not performed in tests
- hardware access: not performed
- OSC send: not performed
- firmware upload: not performed
- browser launch: not performed
- WebSocket server launch: not performed
- live serial path: manual-gated only

## Relation to #152

`#152` は legacy firmware / serial / OSC / robot output boundary parent であり、R7-B completion では閉じない。
R7-B は simulation-facing input pipeline の完了であり、OSC / robot output / actuator command は `#152` 側に残る。

## Parent #216 Close Readiness

`#216` は R7-B parent として close-ready である。

前提は `#217` から `#222` が merged であることだが、これはこの audit 時点で満たされている。
したがって、この audit PR が merge されれば `#216` は close 可能である。

## Remaining Risks

- P1: live serial 実機 validation は未実施
- P1: physical axis / force calibration は未確定
- P2: WebSocket server / browser E2E は未実施
- P2: full pytest は legacy arm_communicator import failure で collection stop する可能性がある
- P3: pyserial 未導入環境では live mode は clear error で停止する
- P3: keyboard helper は OS-level listener ではなく simulation-facing helper である

## Recommended Next Phase

R7-B の次は `R7-C` として manual validation / demo operation package に進めるのが妥当である。

推奨内容:

- human-run live loadcell validation
- viewer launch procedure
- smoke checklist
- recorded demo artifact
- axis sanity check
- presentation-ready operation notes

中間発表向けには simulation-facing pipeline の安定化を優先し、OSC / robot output はまだ推奨しない。

## Validation

docs-only validation として以下を実施する。

- `git diff --check`
- `git status --short`
- `uv run pytest tests/architecture/test_docs_sot.py`

