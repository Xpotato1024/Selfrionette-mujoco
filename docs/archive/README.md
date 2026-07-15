---
status: supporting
owner: architecture
last_verified: 2026-07-16
canonical_for: []
related:
  - docs/architecture/documentation-sot-policy.md
---

# archive

現在仕様または反復運用の責務を終えた文書を、provenanceを維持して保存する。archive内の文書は
historical / retired evidenceであり、current architecture、contract、operationのsource of truthとして扱わない。
既存本文を現在仕様に合わせて改稿せず、必要な場合だけstatus、current SoTへの参照、retired注記を追加する。

- `drafts/`: 未確定のまま終了したdraft
- `proposals/`: 採用前またはretiredしたproposal
- `design/`: 過去時点のdesign note
- `research/`: 過去の調査・比較記録
- `operations/`: 現在の反復手順ではない過去のoperation note
- `historical/`: その他のhistorical record
- `obsolete/`: current useを終了した文書
- `indexes/`: archive、reports、current docsを横断して過去pathと新配置を追跡するindex

全Markdownのmigration後配置は`indexes/docs-index.md`から確認する。
