---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - documentation source of truth policy
related:
  - docs/README.md
---

# 文書Source of Truth方針

## 目的

現在仕様、再利用可能な補足、実装・監査証拠、過去時点の記録を混在させず、現在の判断を少数の正本から辿れる状態を維持する。

## 正本の原則

- 文書rootは`docs/`だけとし、`doc/`を作らない。
- `docs/README.md`をcurrent canonical topicのSource of Truth Mapとする。
- 1 topic = 1 canonical documentとし、同じtopicの正本を複数作らない。
- supporting文書は、補足対象のcanonical documentへlinkする。
- 新規文書を追加する前に、既存canonical documentを更新できないか確認する。
- implementation report、completion audit、inventory、review結果をcurrent specの正本にしない。
- historical evidenceを現在仕様へ合わせて改稿しない。現在の参照先が必要な場合は、provenanceを保ったままstatus注記とcanonical linkを追加する。

## 配置と責務

| 配置 | 責務 |
|---|---|
| `docs/architecture/` | current architecture policy、ownership、dependency boundary |
| `docs/contracts/` | current layer / schema / runtime contract |
| `docs/evaluation/` | current evaluation designとmeasurement contract |
| `docs/operations/` | 反復利用する現在の操作手順・運用規則 |
| `docs/experiment-notes/` | 個別experimentの条件、実行方法、観測結果。architecture正本にはしない |
| `docs/design/adr/` | 設計判断時点の履歴。現在仕様はarchitecture / contractへlinkする |
| `docs/migration/` | legacy移行のinventory、mapping、移行証拠 |
| `docs/reports/implementation/` | Issue / PR単位のimplementation evidence |
| `docs/reports/audits/` | completion audit、review、検証snapshot |
| `docs/reports/inventories/` | inventoryとmigration disposition |
| `docs/archive/` | retired、obsolete、past Round、現在運用ではない記録 |
| `research/logs/` | 月次の実装事実、研究上の価値、未検証事項、判断、次の作業 |

`docs/reports/`は成立事実を保存するevidence領域であり、`docs/operations/`は今も反復できる手順だけを持つ。Issue番号やRound名を持つだけで機械的に分類せず、本文の責務で判定する。

## research logとexperiment notes

- `research/logs/YYYY-MM.md`は研究判断と主張範囲を追記式で記録する。過去の作業や実験結果をIssue / PRから推測して再構築しない。
- `docs/experiment-notes/`は実験条件、model / fixture、command、観測結果を記録する。
- PR本文はactual diffと詳細validation evidenceを記録する。
- 同じvalidation logをresearch logへ複製せず、research logは「何が可能になったか」「研究上どう使えるか」「まだ何を言えないか」を分離する。

## front matter statusとinventory role

front matterの`status`は文書のlifecycleを表す。許可値は次の5つだけとする。

- `canonical`
- `supporting`
- `historical`
- `draft`
- `obsolete`

Markdown inventoryの`proposed role`はmigration判断を表す別軸であり、`canonical`、`supporting`、`evidence`、`historical`、`draft`、`obsolete`、`merge-candidate`を使用する。`evidence`や`merge-candidate`をfront matter statusへ追加しない。

互換関係は次のとおりとする。

| proposed role | migration後の代表的status | 意味 |
|---|---|---|
| `canonical` | `canonical` | current topicの一意な正本 |
| `supporting` | `supporting` | current正本を補足する再利用可能資料 |
| `evidence` | `historical` | 実装・監査・inventoryの時点証拠 |
| `historical` | `historical` | 過去仕様・過去運用・設計判断の記録 |
| `draft` | `draft` | 未確定資料 |
| `obsolete` | `obsolete` | current useを終了した資料 |
| `merge-candidate` | 統合先に従う | current factsを既存canonicalへ統合する候補。統合元は削除しない |

既存front matterの欠落や旧値はinventoryへ明記し、migrationで段階的に解消する。新規または変更する`docs/`文書は許可statusを使用する。

## 日本語とvalidation

人間向け成果物の言語方針は`AGENTS.md`、encoding / BOM / mojibake / GitHub本文の安全規則は`docs/operations/japanese-doc-writing-guardrails.md`を正とする。

validationはUTF-8 decode、BOM、LF、U+FFFD / known mojibake、Markdown relative link、Source of Truth Map target、canonical topic重複、inventory classification、local absolute path、変更本文の日本語方針を確認する。既存英語負債とhistorical evidence内の既知のlocal pathはreport-onlyとし、新規・変更対象へ限定した違反をhard failureにする。
