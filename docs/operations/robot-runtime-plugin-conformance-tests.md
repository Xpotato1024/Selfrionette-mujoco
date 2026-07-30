---
status: supporting
owner: architecture
last_verified: 2026-07-30
canonical_for: []
related:
  - docs/contracts/robot-profile-runtime-viewer-profile.md
  - docs/contracts/fast-arm-joint-limit-config.md
  - docs/operations/validation.md
---

# Robot Runtime Plugin conformance test

## 目的

conformance suiteはproduction Robot Profile、Robot Runtime Plugin、MuJoCo modelが一つの明示contractとして
整合することを検証する。test-only frameworkであり、runtime composition、registration、import、public exportを
追加しない。

## ownership分割

`tests/support/robot_runtime_plugin_conformance.py`がimmutable case type、generic validation helper、common
assertion orderを所有する。robot identity、model path、joint name、site name、expected coordinateを含めない。

`tests/robots/<robot>_conformance_case.py`がproduction profile/plugin selection、profile-owned model /
configuration reference、known qpos / target、expected numeric value、tolerance、model-aligned qpos / endpoint adapterを
所有する。caseは`tests/robots/robot_runtime_plugin_conformance_cases.py`へ明示登録する。

## 必須case field

各caseは次を提供する。

- unique case IDとexpected profile ID
- canonical production profileとruntime plugin object
- profile-owned model asset、home keyframe、endpoint site、joint-limit configuration
- canonical joint orderとqpos/qvel dimension
- 空でないknown FK case collection、reachable IK -> FK case collection、MuJoCo endpoint consistency case collection
- initial `fast_arm` caseは各positive collectionへ意図的に2 casesを持つ。追加caseはrobotのsingularity、coordinate
  frame、joint topology、safety riskに応じて選ぶ
- unitとcoordinate frameを持つ正のfinite tolerance
- identity、model、endpoint、home、configuration mismatch向けfocused fail-closed probe

generic suiteは4 jointを仮定せず、joint countを`nq`または`nv`と同一視しない。異なるqpos layoutを持つ将来modelは
case-owned qpos applicationまたはfeasibility adapterを提供する。

registry validationはfail-fastである。nested case IDは空でなく、collection内でuniqueでなければならない。known-FK
qpos、IK seed-qpos、MuJoCo consistency qposはすべてnumericかつfiniteでなければならない。suiteがexplicit test
registryをloadするときにdeclarationをvalidateし、fail-closed probe自体は後続parametrized testで実行する。

## known value、frame、tolerance

known FK endpointはtest実行前に記録したliteral evidenceである。test対象FK solver、そのFKを使うIK -> FK、同じ
implementationへdelegateするhelperから生成してはならない。各valueはprovenance、unit、coordinate frameを記録する。

IK -> FKはconsistency checkであり、独立FK evidenceを置き換えない。MuJoCo endpoint caseは実modelをloadし、既存の
安全なbackend boundary経由でqposを適用し、snapshot pathで`mj_forward`を実行し、plugin accessorとdeclared siteを
比較する。explicit frame adapterが必要な場合だけrobot caseがmodel-aligned evaluatorを提供する。

endpoint comparisonのtoleranceはmeterで表す。sign、axis、reference-angle、frame errorをrejectできる小ささにする。
fast_arm IK toleranceは既存solverの`1e-5 m` convergence contractに制限し、model/siteとknown-FK checkは
`1e-9 m`を使う。

## robot追加手順

1. canonical production profile/pluginを使い、`tests/robots/<robot>_conformance_case.py`へcaseを定義する。
2. known valueを独立に記録し、そのprovenanceを文書化する。
3. caseを`ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASES`へ明示追加する。filesystem scanning、dynamic import、entry
   point、production registry mutationを使わない。
4. focused caseと関連Python suiteを実行する。

production robot profile/plugin registryがproduction resolutionのsourceであり、test registryはdeterministic case
collectionに限定する。

## checkとcommand

suiteはcase integrity、profile/plugin identity、asset/model contract、home feasibility、known FK、IK -> FK
consistency、MuJoCo site consistency、fail-closed mismatchを検査する。

```bash
uv run pytest tests/runtime/test_robot_runtime_plugin_conformance.py -q
uv run pytest tests/runtime tests/kinematics tests/mujoco_backend tests/architecture -q
uv run python -m compileall -q src tests scripts
git diff --check
```

## non-goalと関連Issue

production behavior、public API、runtime composition、Planar FK/IK、offline runtime smoke、viewer code、payload /
WebSocket behavior、robot asset、hardware pathは変更しない。generic test-double migrationはIssue #387、offline
smokeはIssue #388、public Planar exportはIssue #389、関連cleanup/supporting inventoryはIssue #391で扱う。

後続#388/#389 cleanupでhandoffを消化し、offline smokeはresolved pluginを使い、Planar production
implementation/exportは退役した。このconformance suiteはrobot-specific geometry coverageに留まり、productionへ
移動せず、generic solver algorithmへ拡張していない。
