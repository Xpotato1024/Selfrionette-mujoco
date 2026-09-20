---
status: historical
owner: runtime
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/contracts/pre-hardware-signal-emulation.md
  - docs/design/adr/0009-bounded-sil-validation.md
---

# R7-Lマージ後の受入・残作業点検

## 対象と判断

基点mainは`d57638559264e568479fef22921884dea550210b`（PR #549 merge）。
P0-P4のマージ完了と、実機に接続する運用入口の完成は別である。
本記録は#550の限定修正と既存gateの対応表。固定SHAの実行結果・監査結果は対応PR本文を参照する。
#550未マージ中は、mainに点検で発見した検証不足が残る。親#539を自動closeしない。

## 成立済みの経路と証拠

| gate | 実装・merge | 対応する回帰証拠 |
|---|---|---|
| P0: 全体整合方針 | #545 / PR #546 | ADR 0005、既存architecture tests |
| P1: 連続入力・route/context | #540 / PR #544 | tests/runtime/test_endpoint_route_consistency.py |
| P2: 取得・health有限化 | #541 / PR #547 | Selfrionette source / lifecycle / runtime異常試験 |
| P3: no-I/O protocol peer | #542 / PR #548 | tests/runtime/test_fast_arm_signal_emulation.py |
| P4: 信号→contact→wire/log | #543 / PR #549 | tests/integration/test_signal_contact_e2e.py、named joint group、CLI再生成 |
| マージ後の検証不足修正 | #550 | tests/integration/test_signal_contact_validation.py、既存回帰、固定SHA監査 |

付属fixtureは両sourceで同じscene/Taskを実行する。短い合成条件での成功は人間・実機性能の結果ではない。
P5は未取得の物理evidenceに対してnon-allow、実機出力permissionはdisabledのままである。

## 点検で発見した不足

評価器の追加/unknown指定、診断・終了情報・環境型の矛盾を#550へ追跡する。
修正は対応範囲の明示と既存ownerによる照合であり、新しい汎用runtimeやphysicsを加えない。
正常条件を変えずに元のtraceが一致すること、正しい異常系を読めることを受入に含める。
過去のPASSは当時の検査範囲の記録として保持し、今回の発見をその後の点検結果として追加する。

## 実機なしで残る作業

#551は、#516からsoftware-onlyの入力runtime / physical session / 有限受信driverの接続を切り出したIssueである。
この修正PRでは設計・依存関係の整理までとし、接続実装済みとは扱わない。
本番のaccepted evidenceやoperator permissionを偽装せず、既存test-only fixtureとfake transportによる検証だけを先行する。

#550 merge後に同一tree・CI・受入記録を確認し、親#539の限定SIL gateの最終判定を行う。
「実機前にコード作業が一切残らない」という判定は、#551を含む別の到達点である。

## 実機で残る作業と非対象

#509の安全性測定、#516/#517の実入力・実機運動、#518の接触、#519のphysical completionは未実施。
実配備controller/receiver、校正、停止挙動の確認には別途明示許可が必要である。
UI全軸選択、core外部化、長時間service、動的servo/力制御安定性を、この限定修正の必須条件へ追加しない。
