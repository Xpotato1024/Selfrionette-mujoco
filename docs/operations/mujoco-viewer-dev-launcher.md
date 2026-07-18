---
status: supporting
owner: operations
last_verified: 2026-07-18
canonical_for: []
related:
  - docs/operations/unified-cli.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/websocket-host-port-contract.md
---

# 旧 MuJoCo viewer dev launcher の退役

旧 one-command launcher は、current product route と異なる static viewer path および browser
build command を案内していたため退役した。現在の操作は、目的ごとに次の正本を使う。

- replay / WebSocket publisher: `docs/operations/unified-cli.md`
- viewer smoke: `docs/operations/live-viewer-smoke.md`
- bind host と browser-visible host: `docs/operations/websocket-host-port-contract.md`

AutoPort、process manager、daemon、service を置き換える新機構は追加していない。必要な port は
operator が明示し、使用中の場合は既存 command の failure semantics に従って停止する。
