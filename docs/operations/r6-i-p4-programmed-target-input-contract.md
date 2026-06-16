---
status: canonical
owner: operations
last_verified: 2026-06-16
canonical_for:
  - R6-I-P4 implementation note
related:
  - docs/contracts/programmed-target-input-source.md
  - docs/operations/r6-i-p3-stub-reclassification.md
---

# R6-I-P4 ProgrammedTargetInputSource Contract

## Summary

`ProgrammedTargetInputSource` を追加し、`RawInputFrame.metadata` 経由の programmed target
intent bridge を固定した。

## Scope

- `src/selfrionette/input_sources/programmed_target.py`
- `src/selfrionette/input_sources/__init__.py`
- `tests/input_sources/test_programmed_target_input_source.py`
- `tests/input_interpreters/test_programmed_target_metadata_bridge.py`
- `tests/architecture/test_public_export_policy.py`
- `docs/contracts/programmed-target-input-source.md`
- `docs/contracts/README.md`
- `docs/README.md`
- `docs/operations/r6-i-p4-programmed-target-input-contract.md`

## Changes

- deterministic programmed target frame / trajectory dataclasses を追加した
- `ProgrammedTargetInputSource` を concrete source として追加した
- `loop=False` では terminal frame を返し続ける behavior を固定した
- `loop=True` では sequence が先頭に戻る behavior を固定した
- `RawInputFrame.metadata` に required keys を載せる contract を追加した
- `ReplayInputInterpreter` 経由の metadata bridge を test で固定した
- package-root export に `ProgrammedTargetInputSource` を追加した

## Validation

- pending

## Compatibility

- `RawInputFrame` schema は変更していない
- runtime wiring は変更していない
- dry-run preset の差し替えはしていない
- `sweep_x` 実装は追加していない

## Import Boundary Check

- architecture tests による manual review を予定

## Hardware Validation / Not Run Reason

Hardware Validation: Not run.
Reason: This change does not access hardware, open serial ports, send OSC messages, upload Arduino firmware, or perform network side effects.

## Serial / OSC / Hardware Access

none.

## SoT / Docs Impact

- `docs/contracts/programmed-target-input-source.md` を canonical contract にした
- `docs/README.md` に contract link を追加した
- `docs/contracts/README.md` に canonical contract link を追加した

## Dependency / Merge Order

This PR depends on #153 / #135, #154 / #136, and #155 / #137.
Recommended merge order: #135 -> #136 -> #137 -> #138 -> #139 -> #140 -> #141.
This PR does not implement #139 or later work.

## Remaining Risks

- sweep_x trajectory implementation is deferred to #139.
- dry-run / WebSocket publisher wiring is deferred to later R6-I issues.
- target command schema formalization is deferred to R6-J.
