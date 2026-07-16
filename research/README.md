---
status: canonical
owner: research
last_verified: 2026-07-16
canonical_for:
  - monthly research and implementation log policy
related:
  - docs/architecture/documentation-sot-policy.md
---

# 研究・実装ログ

`research/logs/YYYY-MM.md`へ、研究上の判断と実装の意味を月単位で追記する。過去の作業・実験結果をIssue / PRから推測して再構築しない。

## 記録対象

- runtime behavior、architecture / contract、simulation modelの変更
- evaluation metric / experiment conditionの変更
- 実験可能性や妥当性へ影響するbug fix
- 研究優先順位や主張範囲の決定

単純typo、機械的metadata、研究的意味を持たない保守は、PR本文に更新不要理由を記録すればlog更新を必須としない。

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
