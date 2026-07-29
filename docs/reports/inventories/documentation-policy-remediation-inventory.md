---
status: historical
owner: architecture
last_verified: 2026-07-30
canonical_for: []
related:
  - AGENTS.md
  - docs/architecture/development-policy.md
  - docs/architecture/documentation-sot-policy.md
  - docs/operations/japanese-doc-writing-guardrails.md
  - docs/reports/audits/current-documentation-sot-audit-2026-07-30.md
---

# Issue #483 documentation policy remediation inventory

## 目的

Issue #482 baseline `baabf057e02a8f5e29e51987b3ea25b92ecf6bc4`時点で、comment、docstring、
JSDoc、READMEの恒常ルールをどこへ置くかを整理した#483向け入力である。policy本文ではない。

## current owner候補

| concern | current owner / routing | current state | #483 action |
| --- | --- | --- | --- |
| repository-local autonomy / scope / completion | `AGENTS.md` | current | 詳細policyへのroutingだけを追加する |
| human-facing language | `AGENTS.md` | current | 日本語原則をcode documentationへどう適用するか定義する |
| document role / SoT / metadata | `docs/architecture/documentation-sot-policy.md` | current | READMEとcode documentationのcanonical関係を補う |
| general development quality | `docs/architecture/development-policy.md` | current | 詳細を重複せずpolicy ownerへroutingする |
| encoding / mojibake / GitHub transport | `docs/operations/japanese-doc-writing-guardrails.md` | current | transport ruleはここに保持する |
| comment / docstring / JSDoc | ownerなし | missing | 一意なcanonical ownerを定義する |
| TODO / FIXME | ownerなし | missing | owner、必須context、retirement conditionを定義する |
| commented-out code | ownerなし | missing | 原則禁止と例外条件を定義する |
| plugin / directory README | ownerなし | missing | 作成要否、責務、重複禁止を定義する |

## 推奨canonical owner

`docs/architecture/code-documentation-policy.md`を新しい一意owner候補とする。名称は#483開始時に
`docs/README.md`のtopic構成を再確認して確定する。`AGENTS.md`、
`development-policy.md`、`documentation-sot-policy.md`には恒常routingと境界だけを置き、
同じrule本文を複製しない。

## #483で決定する事項

1. Python public surface、TypeScript exported surface、plugin entry pointをどの単位でdocumentするか。
2. private helper、thin wrapper、re-export、Protocol / TypedDict / dataclassに必要な説明量。
3. unit、coordinate frame、lifecycle、side effect、failure mode、compatibility rationaleの必須条件。
4. What / Howだけを繰り返すcommentと、Why / invariantを記録するcommentの区別。
5. TODO / FIXMEのowner、Issue link、期限またはretirement condition。
6. commented-out code、historical PR / date comment、suppression commentの扱い。
7. `# noqa`、`type: ignore`、lint disableへ理由を要求する範囲。
8. READMEが必要なdirectoryと不要なprivate / generated directoryの判定。
9. plugin root、axis、concrete plugin READMEの責務とcanonical docsへのrouting。
10. Japanese language policyをidentifier、protocol literal、外部formal nameへ誤適用しないvalidation。
11. policyをarchitecture test / validatorでどこまで機械検査するか。

## 重複を避ける境界

- SoT role、front matter、canonical topicは既存`documentation-sot-policy.md`を正とする。
- UTF-8、BOM、mojibake、GitHub body transportは既存guardrailを正とする。
- runtime / plugin architectureの説明は各canonical architecture / contractを正とし、policyへ複製しない。
- READMEは入口とlocal責務を担い、full architecture contractを再掲しない。

## #482で行っていないこと

`AGENTS.md`への先取りrule追加、policy文書新設、repository-wide comment / docstring / JSDoc修正、
README hierarchy作成は行っていない。#483は#482 headからbranchを作り、policy決定とroutingだけを扱う。
