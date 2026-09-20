---
status: historical
owner: runtime
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/contracts/pre-hardware-signal-emulation.md
  - docs/design/adr/0008-signal-contact-integration.md
---

# ADR 0009: 有限SILの対応範囲を実行前に検証し、記録内の整合性を照合する

## 背景

PR #549マージ後の点検で、評価器の2件目以降が無視され、unknownな先頭評価器も実行後にしか拒否されないことを確認した。
traceのruntime_safety、終了index・reason、MuJoCo versionも、再hashした矛盾した値が読戻しを通った。
#550ではこの受入境界を修正する。汎用experiment control planeや物理検証は対象外とする。

## 決定

現行runnerはcontact_outcome/v1を正確に1件だけ受理し、reader/model開始前に解決する。
複数評価器の宣言を受理して一部だけ実行しない。将来の複数評価器対応は、全結果のschemaと受入を別途設計する。

診断は原入力から検証済みのsource状態、保存candidate、現在姿勢に既存input safety / Robot joint-limit guardを再適用して照合する。
solverやphysicsは再実装しない。candidateとphysicsが本当に観測されたことの証明ではなく、保存された値同士の整合検証である。
既存Robot APIでbase modelをload/validateしてguardを取得する。新provider APIや具体plugin importの許可例外を増やさず、simulation stepは行わない。

Taskの最後のadvanceと、入力budget終了後のfinalizeを区別する。前者がrunningのままなのに、後者のfailureをTask自然終了の証拠に使わない。
終了kindごとのindex、件数、応答、理由と例外型を照合し、実行終了後の追加commandや空の原因情報を受け入れない。

MuJoCo versionは3つの数値componentと任意のASCII版suffixを持つ128文字以下の文字列として検証する。
読取り環境と版が違うだけで旧記録を拒否せず、版文字列の正しさや同一実行環境を暗黙に認定しない。

## 却下した代案

この修正だけのためのmulti-evaluator framework、署名基盤、別physics再生engineは導入しない。
無検証fieldを一律削除する案も、既存trace利用者と原因追跡を壊すため採用しない。
既存schema名と正常fixtureの出力を維持し、既存record内で矛盾する値の受入だけを狭める。

## 受入と制限

unknown/追加/version違いの評価器、偽診断、bool/int混同、終了index・reason改変、版型違いの反例を試験する。
正しいstale/reject/hold/取得失敗/cleanup failure/未完了Taskを読めることも同時に検証する。
hashは署名ではなく、整合する完全な捏造や任意の内部例外の真正性は保証しない。
実機用sessionのsoftware接続は#551へ分離し、実機の校正・受理・停止は#509/#516以降に残す。
