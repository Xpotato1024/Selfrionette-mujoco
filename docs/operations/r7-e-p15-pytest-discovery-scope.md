# R7-E follow-up P15: pytest discovery scope

## Status

P15 の validation / tooling 設定。root の canonical pytest discovery を current `tests/` に固定する。production code、test implementation、legacy、CI workflow は変更しない。

## Numbering / SoT

- Numbering SoT: Issue #293
- Parent: #324
- Round: R7-E follow-up Batch 1
- Slot: P15
- Issue: #352
- Dependency: P8 / #343 / PR #344 completed
- P10 / #347、P11 / #348 とは独立した maintenance track

## Problem

P15 より前の root `uv run pytest` は repository 全体を暗黙探索し、reference-only の `legacy/fast_arm_control/mujoco_sim/test_controller.py` を collection 対象に含めていた。その結果、current test suite の実行前に `ModuleNotFoundError: No module named 'arm_communicator'` で停止していた。

`legacy/` は参照元であり、current implementation や canonical validation の test root ではない。P15 は legacy module の import failure を修復せず、canonical discovery boundary を明示する。

## Canonical Test Entry

repository root で次を実行する。

```bash
uv run pytest
```

targeted current test は `tests/` 配下の path を明示して実行できる。

```bash
uv run pytest tests/architecture
uv run pytest tests/runtime/test_runtime_input_source_step_loop.py
```

## Discovery Scope

root `pytest.ini` は `testpaths = tests` を定義し、canonical collection root を current `tests/` のみに固定する。

暗黙再帰から次を除外する。

- `legacy`
- `node_modules`
- `dist`
- `artifacts`
- `.git`
- `.venv`

これらは reference-only、dependency、generated、local artifact、または tool-managed directory であり、canonical current Python suite の collection root ではない。

## Legacy Reference-only Boundary

- `legacy/` の source は残す。
- legacy file を移動、rename、編集、import、実行、修復しない。
- `arm_communicator` の fake module を追加しない。
- legacy test に skip / xfail を追加しない。
- canonical result を通すために current test を skip / xfail しない。

P15 が変更するのは pytest の root canonical discovery scope だけであり、legacy code の support status や動作を変更しない。

## CI Relationship

`.github/workflows/ci.yml` の `python-validation` は current test directories をすでに明示列挙しており、`legacy/` を実行しない。P15 は CI workflow、CI command、dependency、pytest plugin を変更しない。

root canonical command と CI はどちらも current `tests/` を検証対象とする。ただし、CI の明示的な directory list を root command へ置き換えることは P15 の scope 外である。

## Explicit Legacy Invocation

`uv run pytest legacy/...` のように legacy path を明示する実行は canonical validation の外であり、unsupported のままでよい。`testpaths` と `norecursedirs` は explicit legacy invocation の互換性や成功を保証しない。

## Compatibility

- production behavior changed: no
- root canonical `uv run pytest` collection changed: yes
- tests moved: no
- test semantics changed: no
- legacy changed: no
- CI changed: no
- dependency / plugin added: no
- public API / schema changed: no
- import boundary changed: no
- MuJoCo XML / assets changed: no

将来 canonical current test root が `tests/` 以外へ拡張される場合は、追加 root の ownership と CI coverage を確認し、`pytest.ini` の `testpaths` と本 document を同じ変更で更新する。単に legacy collection を再有効化する rollback は行わない。

## Validation

- `uv run pytest --collect-only -q`: current `tests/` を collection し、`legacy/` を含まないことを確認する。
- `uv run pytest`: canonical current suite が legacy `arm_communicator` collection error なしで完了することを確認する。
- `uv run pytest tests/architecture`: architecture boundary が維持されることを確認する。
- `uv run python -m compileall src tests scripts`: current Python source を compile 検証する。
- `git diff --check`: whitespace / patch hygiene を確認する。
- UTF-8 without BOM、mojibake、allowed changed files、CI workflow unchanged を静的確認する。

viewer typecheck、build、tests は実行しない。変更対象が pytest discovery config と docs のみで、viewer/frontend file を変更しないためであり、blocker ではない。

## Hardware / External Effects

- hardware validation: not run
- reason: pytest discovery configuration / documentation only
- serial port opened: no
- Arduino upload: no
- OSC sent: no
- robot output: no
- Selfrionette hardware accessed: no
- runtime external network side effect: no
- browser backend server launched: no
