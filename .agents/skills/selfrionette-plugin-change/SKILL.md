---
name: selfrionette-plugin-change
description: Selfrionette-mujocoのRobot、Environment、Mapping、Task、Evaluation、Input Sourceに対するplugin追加・material変更を、contract・ownership・discovery・composition・docs・testsの境界から監査する。plugin変更の実装またはreview前に使用する。
---

# Selfrionette plugin change

## Triggerとexclusion

6 axisのplugin追加、登録、発見、identity、runtime composition、ownership、resource、README、
contract変更を扱うときに使用する。単なる一般docs修正、単発fixture、既存behaviorの無関係なcleanup、
pluginと無関係なstub、不要なcompat layer、parallel implementationは対象外である。current Issue、
branch、SHA、特定実装の一時状態をSkill本文へ固定しない。

## Required inputsと取得方法

- `AGENTS.md`、`docs/README.md`、`docs/architecture/dependency-boundaries.md`、
  `docs/architecture/runtime-composition.md`を読む。
- 対象axisのcontract、axis README、plugin-local README、catalog / registration / discoveryを取得する。
- actual diff、consumer、tests、関連canonical docs、research / experiment impact条件を確認する。
- pluginのlogical identity、version、resource、lifecycle、side effect、failure semanticsを実装から確認する。

不明なownership、duplicate identity、version mismatch、未登録path、またはcurrent SoT間の矛盾は推測で補完しない。

## Ordered workflow

1. 対象axisをRobot、Environment、Mapping、Task、Evaluation、Input Sourceのいずれかに限定する。
2. axis contract、owner、入力・出力、lifecycle、side effect、failure semanticsを照合する。
3. discovery、identity、registration / catalog、version compatibility、resource ownershipを確認する。
4. runtime composition rootへの接続、viewer safety、legacy import、parallel implementationの有無を監査する。
5. plugin-local README、axis README、canonical docs、focused / architecture testsの必要性を確認する。
6. Documentation impact、Research log impact、Experiment evidence impactを実質的影響で判定する。
7. `selfrionette-change-validation`へvalidationをrouteし、scope外の不足は停止条件として報告する。

## Permitted variation

axisごとにcatalog、resource、runner、README、lifecycleの具体的ownerは異なる。既存のcanonical
contract、実装、testsの組合せを選び、未実装のaxisへplanned behaviorをcurrent behaviorとして追加しない。

## OutputsとDefinition of Done

出力は、axis、contract、ownership、discovery、identity、registration、composition、README、tests、
canonical docs、3つのimpact判定、selected validation、残存riskを含む監査結果とする。

完了条件は、plugin追加と無関係なstub・compat layer・parallel implementationがなく、logical identityと
contractが一意で、runtime compositionとresource ownershipがSoTに一致し、必要なREADME・docs・testsの要否を実測していることである。

## Failure、retry、stop / escalation

unknown、duplicate、version mismatch、missing capability、ambiguous owner、暗黙fallback、または
必要なpublic schema / contract変更が見つかったらfail closedで停止する。read-only再取得でcurrent stateを一度確認し、
矛盾が残る場合は実装を広げずユーザーへescalateする。

## Side-effect boundary

instruction-onlyのread/validationを基本とする。許可された変更task内のdocs、tests、plugin documentationだけを対象にし、
runtime、viewer、simulation、hardware、serial、OSC、production、credentials、external serviceを変更・操作しない。
