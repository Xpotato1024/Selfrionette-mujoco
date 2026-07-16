---
status: canonical
owner: architecture
last_verified: 2026-07-17
canonical_for:
  - runtime composition root
related:
  - docs/architecture/data-flow.md
  - docs/contracts/parallel-work-contracts.md
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# runtime composition

`runtime/` is the only composition root。input、motion、kinematics、MuJoCo backend、transportを
layer横断で接続できるのはruntimeだけである。MuJoCo remains the physical source of truth。
viewerはrender-onlyであり、runtime stateを再計算しない。

production compositionは明示的に選択した`RobotRuntimePlugin`を解決し、model、joint order、
startup keyframe、IK / FK、motion policy、qpos feasibility guardの整合を検証する。generic stub、
zero solver、退役したPlanar solverへ暗黙fallbackしない。

実験compositionでは、Robot Bundle、Environment / Scene、Control / Mapping、Task、Evaluationを
versioned known-ID registryから明示解決する。`runtime/`はphysicsやrunner開始前にcapability provider、
axis-scoped parameter owner、typed semantic role、version-aware robot/environment/task compatibility、
evidence producer、evaluator requirementをfail-closedで検証する。詳細なtyped contractとreadiness順序は
`docs/contracts/experiment-plugin-composition.md`を正とする。

## composition-rootの責務分割

| stage | 現在のowner | 抽出可能なboundary | authoritative input | authoritative output / failure |
| --- | --- | --- | --- | --- |
| source planning | runtime entry | input-source registry resolver | configurationとsource ID | validated source planまたは明示的なunknown / incompatible failure |
| source lifecycle | runtime loop | source lifecycle coordinator | selected sourceとclock | latest `InputIntent`、source activity、age |
| control-frame resolution | runtime control-frame resolver | pure frame resolver | requested frame、pre-step orientation、`dt_s` | resolved world intentまたはunavailable status |
| motion policy | selected plugin / runtime coordinator | motion policy adapter | intent、current qpos、target lifecycle | `MotionCommand`またはhold / reject |
| backend update | MuJoCo backend boundary | backend command applier | validated whole qpos candidate | updated model stateまたは適用前failure |
| MuJoCo measurement | post-step measurement helper | pure measurement helper | post-step `MuJoCoState` | physical `tip` site measurement |
| diagnostic annotation | runtime diagnostics | pure annotator | intent、prediction、measurement、source state | precedenceを固定したmetadata |
| publication | runtime publication coordinator | `StatePublisher` | fully annotated state | publication completion |
| target lifecycle | runtime target resolver | pure lifecycle reducer | desired / active / measured target evidence | authoritative active targetまたはhold |
| experiment record construction | explicit caller-owned adapter | production loop外のrecord builder | completed step evidence | immutable record。default runtimeはfileを開かない |
| experiment plugin readiness | runtime composition | versioned plugin resolver | explicit 5-axis selectionとaxis-scoped typed parameter | resolved capability、typed role、evidence producer bindingまたはstartup failure |

## failureとordering

- unknown profile、incompatible model、invalid joint orderはcomposition前に失敗する。
- qpos feasibilityはcandidate全体を検証し、invalid candidateを部分適用しない。
- stale / inactive sourceはhold-current semanticsを優先し、新しいactive targetを捏造しない。
- unavailable diagnostic fieldは欠落のままとし、stale値を保持しない。
- `publish-before-`ViewerInputSource`-rebase ordering`を維持する。
- transport failureをphysics successへ読み替えず、viewer failureをbackend stateへ反映しない。

この文書はcurrent responsibility boundaryを固定し、does not perform a broad runtime rewrite。
pre-audit composition chronologyとrefactor proposalは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
