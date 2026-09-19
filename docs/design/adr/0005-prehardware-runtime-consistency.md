---
status: historical
owner: architecture
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/architecture/research-execution-roadmap.md
  - docs/contracts/experiment-plugin-composition.md
  - docs/reports/audits/r7-l-consistency-baseline-2026-09-20.md
---

# ADR 0005: SIL前にroute・context・policyの整合を確定する

## 状態

2026-09-20のユーザー方針に基づく採用設計。実装済みであることを意味しない。
#545で調査・判断を記録し、#540-#543で段階実装する。current contractは対応PRで更新する。

## 背景

PR #544の同一delta routeが実行入口によって異なるjoint commandを作ることを確認した。
局所的にcapを外す、metadataを追加するだけでは再現性の問題を解消しない。

## 決定

1. production delta routeは専用typed execution bindingを持ち、明示的なdelta methodでlocal solverを呼ぶ。
   velocity経路は既存update methodを使用する。metadataのlabelは観測用であって実行方式のauthorityではない。
2. local generator選択もtyped route capabilityに置き、同じbindingをconcrete builder、step loop、pipelineから使う。
   replay/absolute-targetのcompatibility helperは別経路とし、そのsolverや結果を変更しない。
3. context parameter名はMappingが宣言する。runtime readinessだけがその宣言済み項目の後段供給を許し、
  純粋関数向けnormalize/validationは引き続きfull parameterを要求する。未知field・不正型の拒否は維持する。
4. 同一pre-step MuJoCo snapshotから測定したendpointをruntimeが供給する。欠落・非finiteはfail-closed。
   selectionの固定parametersを変更せず、観測していないzeroや任意anchorで埋めない。
5. 既存software motion bound（endpoint norm 0.01 m、joint norm 0.2 rad）とDLS数値は維持する。
   unmapped raw signal、Mapping要求、policy後delta、candidate/request qpos、post-step observationを分離する。
   policyの値・identityとraw requested deltaを記録し、制約がexperiment interpretationへ与える影響を見える形にする。
6. standalone current-tip fieldをphysical measurement authorityへ昇格しない。実機のevidence gateは一切緩めない。
7. code、consumer、contract、testを同じreview単位で整合させる。旧監査の誤った断定も保存した上で訂正する。

## 代案と却下理由

- capを削除/0.03へ増やすhotfix: physical根拠がなく、既存software safety/conditioningを変えるため却下。
- すべてのlayerを一度にrewrite: 差分の検証境界が失われるため却下。
- current tipを必須placeholderのまま放置: runtimeとfrozen conditionの責務を曖昧にするため却下。
- source kindごとにrun_onceへ分岐を追加: 同じ欠陥を別入口へ複製するため却下。
- 既存wire schemaの全面version-up: 今回は内部境界の追加で対処できるため採用しない。

## 移行と検証

#540では既存legacy callersを維持した追加APIとし、同一source/mapping/route/configから得た
step-loopとrun_onceの指令一致、明示deltaのdt非依存、velocityのdt積分、cap跨ぎ、zero、failure cleanupを確認する。
R7-Gのworld/tool、replay、viewerの既存挙動を回帰する。#541-#543はこの受入後に進む。
時点ごとのSHAと残存gateを記録し、実機前completionは#543の統合受入後だけ宣言する。
