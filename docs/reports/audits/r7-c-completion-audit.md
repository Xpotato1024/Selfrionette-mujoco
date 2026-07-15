---
status: historical
owner: operations
last_verified: 2026-06-22
canonical_for:
  - R7-C completion audit
related:
  - docs/README.md
  - docs/operations/r7-c-manual-validation-preflight.md
  - docs/operations/r7-c-viewer-fixture-demo-procedure.md
  - docs/operations/r7-c-keyboard-replay-demo-package.md
  - docs/operations/r7-c-live-loadcell-validation-log.md
  - docs/operations/r7-c-axis-sanity-check.md
  - docs/operations/r7-c-presentation-demo-notes.md
  - docs/operations/hardware-safety.md
---

# R7-C completion audit

## Scope

この audit は #238 の docs / audit only であり、R7-C manual validation / demo operation package の
完了状態と parent #231 close-readiness を判定する。

この audit では runtime 実装、viewer 実装、serial 実行、COM access、hardware validation、
OSC send、robot output、actuator command は行わない。

## Completed Issues

| Issue | PR | Status | Notes |
|---|---|---|---|
| #232 | #239 | merged | manual validation preflight |
| #233 | #240 | merged | viewer launch and fixture demo procedure |
| #234 | #241 | merged | keyboard / replay demo package |
| #235 | #242 | merged | live loadcell validation log template |
| #236 | #243 | merged | axis sanity check protocol |
| #237 | #244 | merged | presentation-ready demo notes |
| #238 | #245 | merged | this completion audit |

Merge order:

```text
#232 -> #233 -> #234 -> #235 -> #236 -> #237 -> #238
```

Review order:

```text
#232 -> #233 -> #234 -> #235 -> #236 -> #237 -> #238
```

## Proven

- R7-C manual validation preflight が docs SoT に登録されている
- viewer launch / fixture demo procedure が存在する
- keyboard / replay demo package が存在する
- manual live loadcell validation log template が存在する
- axis sanity check protocol と template が存在する
- presentation-ready demo notes が存在する
- `desired_endpoint_m` は command-side endpoint として説明されている
- `target_position_m` は primary command ではなく viewer feedback / compatibility field として説明されている
- `endpoint_evaluation` は read-only optional diagnostic として説明されている
- Codex / CI は serial / COM / hardware / OSC / browser / WebSocket server を実行しない境界が明記されている

## Intentionally Unproven

- real robot output
- actuator command
- OSC send
- firmware upload / modification
- live serial validation by Codex / CI
- COM access by Codex / CI
- browser E2E by Codex / CI
- WebSocket server launch by Codex / CI
- hardware validation by Codex / CI
- physical axis finalization
- force unit calibration
- final loadcell-to-axis mapping
- production demo automation

## Safety / Access Confirmation

R7-C audit 時点で、以下は Codex / CI によって実施していない。

- serial port opened: no
- COM access: no
- OSC sent: no
- Arduino upload: no
- firmware modified: no
- hardware validation included: no
- real robot output: no
- actuator command: no
- browser E2E launched in CI: no
- WebSocket server launched in CI: no

Human-run live serial は #235 の template で manual gate 後に記録する対象であり、
この audit の実行対象ではない。

## Demo Readiness

R7-C は中間発表に向けて close-ready と判定する。

理由:

- no-hardware preflight が固定された
- viewer / fixture demo procedure が固定された
- keyboard / replay demo package が固定された
- live loadcell は manual-gated log template として扱える
- axis sanity は final calibration ではなく pass / caution / fail として記録できる
- presentation notes が proven / intentionally unproven を分離している
- fallback demo plan がある

## Post-merge Metadata Correction

#244 / #245 の PR body は merge 操作時に簡略化されたが、repo docs を source of truth とする。
presentation-ready demo notes には demo narrative / fallback / proven-unproven が残っており、
この completion audit には R7-C close readiness、#152 open 維持、no serial / hardware / OSC /
browser / WebSocket server boundary が残っている。追加の PR metadata correction は不要である。

## Parent #231 Close Readiness

Parent #231 is close-ready once this post-merge correction PR is merged.

Close-ready の理由:

- #232 から #237 の R7-C child scope が docs と template としてそろっている
- R7-C の demo workflow は human-run / no-hardware / manual-gated の境界で説明可能である
- safety / access boundary が各 PR body と docs に残っている
- #152 を閉じず、OSC / robot output / actuator command boundary parent として open 維持する方針が明記されている

## Remaining Risks

- P1: live loadcell validation は人間の manual run が必要
- P1: physical axis finalization / force calibration は未実施
- P2: browser / WebSocket server の actual demo は Codex / CI では未実施
- P2: recorded artifact の採用判断は発表当日の状況に依存する
- P3: pyserial unavailable の環境では live serial は caution / fail として記録する必要がある

## Recommended Next Phase

次 phase は #152 を open 維持したまま、OSC / robot output / actuator command boundary を別 parent / child で扱う。

推奨:

- R7-C PR stack を順に review / merge する
- #231 を #238 merge 後に close する
- #152 は legacy firmware / serial / OSC / robot output boundary parent として open 維持する
- 実機制御や actuator command は、R7-C の manual validation docs と切り離して別 phase で扱う

## Validation

この audit PR で実施する validation:

```powershell
git diff --check
uv run pytest tests/architecture/test_docs_sot.py
uv run python -m compileall src tests scripts
```

日本語 docs を編集したため、UTF-8 / BOM / mojibake check も実施する。

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
