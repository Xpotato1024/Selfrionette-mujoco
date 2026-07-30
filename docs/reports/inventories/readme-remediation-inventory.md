---
status: historical
owner: architecture
last_verified: 2026-07-30
canonical_for: []
related:
  - README.md
  - docs/README.md
  - docs/reports/audits/current-documentation-sot-audit-2026-07-30.md
  - docs/reports/inventories/documentation-policy-remediation-inventory.md
---

# Issue #484 README remediation inventory

## 目的とbaseline

Issue #482 baseline `baabf057e02a8f5e29e51987b3ea25b92ecf6bc4`のtracked README 24件と
missing human-facing entry pointを分類した#484向け入力である。#482では明白なfalse / stale記述だけを
修正し、README hierarchyは作成していない。

## existing README 24件

| path / group | count | #482 state | #484 recommended action | priority |
| --- | ---: | --- | --- | --- |
| `README.md` | 1 | current SoT routingを修正 | architecture / plugin / directory入口を簡潔に整備 | P1 update |
| `apps/mujoco-viewer/README.md` | 1 | current、Issue固有履歴が多い | operator入口とcanonical routeを残し、履歴をreportへ分離 | P1 update |
| `docs/README.md` | 1 | Source of Truth Mapを全canonicalへ同期 | Map ownerとして維持 | P0 retain |
| `docs/{architecture,contracts,operations}/README.md` | 3 | current index | topic入口と重複を確認して維持 | P1 update |
| `docs/{design,design/adr}/README.md` | 2 | current index | design / ADRのroleだけを維持 | P2 update |
| `docs/{archive,migration,reports}/README.md` | 3 | historical routing | current SoTでないことを維持 | P1 retain/update |
| `docs/experiment-notes/README.md` | 1 | canonical operation | experiment evidence入口として維持 | P0 retain |
| `research/README.md` | 1 | canonical research operation | research log gateとして維持 | P0 retain |
| `firmware/README.md` | 1 | hardware入口 | safety / canonical operation routeを確認 | P1 update |
| `firmware/arduino/README.md` | 1 | hardware入口 | active / legacy boundaryを明示 | P1 update |
| `firmware/arduino/legacy_selfrionette/**/README.md` | 3 | legacy provenance | historical用途を明示し、current手順へ改稿しない | P1 update |
| `src/selfrionette/{kinematics,motion,mujoco_backend,runtime,transport}/README.md` | 5 | retired path / ownershipを#482で修正 | #483 policyに従いlocal responsibilityとcanonical routeを統一 | P1 update |
| `src/selfrionette/schemas/README.md` | 1 | current | schema domain入口として維持 | P1 update |

## missing plugin README

次の18件を#484の主要create対象とする。

| owner path | purpose | priority |
| --- | --- | --- |
| `src/selfrionette/plugins/README.md` | 共通bounded discoveryとaxis ownershipへの入口 | P0 create |
| `plugins/robots/README.md` | Robot catalog / discovery / registration / Bundle | P0 create |
| `plugins/input_sources/README.md` | Input Source catalog / discovery / registration / lifecycle | P0 create |
| `plugins/mappings/README.md` | Mapping catalog / discovery、registrationなし、2 private shared owners | P0 create |
| `plugins/environments/README.md` | generic axisだけが存在しproduction concrete未接続 | P1 create |
| `plugins/tasks/README.md` | generic axisだけが存在しproduction concrete未接続 | P1 create |
| `plugins/evaluations/README.md` | generic axisだけが存在しproduction concrete未接続 | P1 create |
| `plugins/robots/fast_arm/README.md` | logical identity、Bundle、adapter / core、resource入口 | P0 create |
| `plugins/input_sources/{analog_fixture,noop,programmed_target,replay,selfrionette,viewer}/README.md` | concrete source contract、lifecycle、compatible Mapping | P1 create × 6 |
| `plugins/mappings/{analog_fixture_mapping,loadcell_endpoint_mapping,replay_mapping,viewer_keyboard_gamepad_mapping}/README.md` | command semantics routeとlocal behavior | P1 create × 4 |

package basenameとlogical identityを同一視せず、concrete READMEはcatalog宣言を複製したplugin listの
正本にしない。current identityとresourceはactual plugin declarationへlinkする。

## other entry-point candidates

| path | finding | recommended action | priority |
| --- | --- | --- | --- |
| `src/selfrionette/README.md` | package layer全体の入口なし | architecture / schema / plugin / runtime READMEへのrouteを作る | P1 create |
| `scripts/README.md` | 16 tracked scriptsの安全区分入口なし | repository / viewer / diagnostics / hardwareを区分する | P1 create |
| `tests/README.md` | 197 tracked test/support filesのownership入口なし | architecture / schema / runtime / integrationの責務を案内する | P2 create |

baselineで`assets/`、`configs/`、`experiments/`にtracked fileはないため、空directoryを想定したREADMEは
作らない。将来tracked contentが追加された時点で再判定する。

## README不要とするdirectory

- `_command_routes.py`と`_continuous_endpoint_velocity.py`等のprivate helper単位: axis READMEがownerとなる。
- runtime internal subdirectory、schema subdomain、test fixture / supportの各小directory:
  public entry pointではなく、親READMEとcode documentationで足りる。
- `node_modules/`、`dist/`、`.vite/`、`artifacts/`、`.pytest_cache/`等のgenerated / local directory:
  tracked対象ではなくREADMEを置かない。
- historical report個別directory: `docs/reports/README.md`のroutingで足りる。

## stale / link result

#482後のtracked Markdown relative link破損は0件、current READMEのretired path / stale ownershipは0件である。
#484ではarchitecture contractをREADMEへ複製せず、entry point、local responsibility、canonical route、
operatorが最初に必要なcommandだけを整備する。
