---
status: canonical
owner: research
last_verified: 2026-07-16
canonical_for:
  - monthly research and implementation log policy
related:
  - docs/architecture/documentation-sot-policy.md
  - AGENTS.md
  - docs/experiment-notes/README.md
---

# 研究・実装ログ

`research/logs/YYYY-MM.md`へ、研究上の判断と実装の意味を月単位で追記する。過去の作業・実験結果をIssue / PRから推測して再構築しない。

## 判断原則

research logの要否は、変更したファイルやdirectoryではなく、研究上の能力・判断・主張への実質的影響で判定する。

次のいずれかが変わる場合は、当月logを更新する。

- 研究で実行または評価できる対象
- simulation、runtime、model、architecture、contractの研究利用上の能力または制約
- experiment condition、evaluation metric、比較条件、測定方法
- 研究上の解釈、優先順位、仮説、主張範囲
- 実験可能性、妥当性、再現性に影響するbug fix
- 研究上の判断に使う成立事実または既知limitation

次は、上記の実質的影響を持たない限り原則として更新不要である。

- `AGENTS.md`、workflow、formatting、typo、機械的metadataだけの変更
- documentation governance、文書配置、翻訳、link repairだけの変更
- CI、validator、repository hygieneだけの変更
- branch、PR、Issue、release等のGitHub運用だけの変更
- production behavior、experiment condition、research decisionを変えないrefactor
- test、compile、typecheck、build、通常smokeを再実行しただけの作業

上記の保守変更でも、研究で可能なこと、実験条件、判断、仮説、主張範囲、妥当性または再現性を実質的に変える場合は更新対象とする。例えばvalidator修正で過去の評価結果が無効になる場合や、docs-onlyのcontract訂正によって研究上の前提が変わる場合は、ファイル種別にかかわらず記録する。

## 作業ごとの判定手順

1. 研究で実行・評価できること、実験条件、研究判断または主張範囲が変わるかを確認する。
2. 変わる場合は当月logを更新する。
3. experiment condition、model / fixture、実行command、観測結果を新規取得または変更した場合は、`docs/experiment-notes/`へ記録する。
4. research log対象外の場合は、PR本文または最終報告へ簡潔な更新不要理由を記録する。

experiment notesへ観測事実を記録したことだけでresearch logが必須になるわけではない。観測によって研究上の解釈、判断、可能性、limitation、次の優先順位が変わった場合にresearch logも更新する。

## entry template

```markdown
## YYYY-MM-DD: 作業名

- 日付:
- 目的:
- 実施内容:
- 検証:
- 現在できるようになったこと:
- 実験的価値:
- まだ言えないこと:
- 判断:
- 未解決事項:
- 次の作業:
- 関連Issue / PR / commit:
```

詳細なcommand出力やtest matrixはPR本文または`docs/reports/`へ置き、ここでは実装事実、実験的価値、未検証事項を分離する。個別experimentの条件と観測結果は`docs/experiment-notes/`へ置く。
