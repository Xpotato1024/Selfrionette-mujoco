---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - R6-G-P3 startup script gap audit
  - backend / viewer launch helper decision
  - startup script minimal completion
related:
  - README.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/r6-g-p1-startup-path-audit.md
  - docs/operations/japanese-doc-writing-guardrails.md
---

# R6-G-P3 Startup Script Gap Audit

## 目的

R6-G-P1 / P2 で文書化した backend / dry-run / WebSocket publisher / Web viewer /
browser 接続導線を前提に、起動 script / wrapper / npm script の不足が残るかを
確認し、必要な場合のみ最小補完する。

## 既存起動導線

- backend / dry-run は `scripts/run_replay_mujoco_dry_run.py`
- WebSocket publisher は `scripts/run_replay_mujoco_websocket_publisher.py`
- live viewer smoke は `scripts/run_live_viewer_smoke.py`
- browser viewer build は `apps/mujoco-viewer` 配下の `npm ci` と
  `npm run browser:build`
- browser 接続は `apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766`
  で明示する

## 不足分類

- A. 既存 script で足りている
  - backend / dry-run
  - WebSocket publisher
  - live viewer smoke
- B. README / docs の説明だけで足りる
  - browser page URL と WebSocket URL の区別
  - `127.0.0.1` / `localhost` と `0.0.0.0` の区別
  - browser から見える host を URL に使う説明
- C. thin wrapper があると明確に改善する
  - 今回は該当なし
- D. npm script 追加が必要
  - 今回は該当なし
- E. scope 外なので今は扱わない
  - public host / LAN / Tailscale の host / port contract の詳細整理
  - troubleshooting の拡充

## 補完判断

既存 script と既存 README / docs だけで loopback 再現導線は成立する。
R6-G-P3 では新規 script は追加しない。

## 追加した script / wrapper

- なし

## 追加しなかったもの

- 新規 Python script
- 新規 npm script
- Windows / PowerShell 専用 wrapper
- 0.0.0.0 bind と browser URL を自動組み立てする helper

## README / docs への反映

- `README.md` に R6-G-P3 audit の参照を追加した
- `docs/README.md` に本 audit を SoT map へ追加した
- `docs/operations/backend-viewer-startup.md` に「不足なし」判断を固定した
- `apps/mujoco-viewer/README.md` に既存導線依存であることを追記した

## R6-G-P4 への handoff

- public host / LAN / Tailscale の URL contract は R6-G-P4 で扱う
- `0.0.0.0` と browser から見える host の整理は R6-G-P4 に渡す
- 正本となる contract 文書は `docs/operations/websocket-host-port-contract.md` とする

## R6-G-P5 への handoff

- live viewer smoke の troubleshooting は R6-G-P5 で拡充する
- browser 接続失敗時の切り分けは R6-G-P5 に渡す

## Non-Goals

- production server
- auth / TLS / reverse proxy
- hardware validation
- serial port open
- OSC send
- viewer visual feature
- viewer-side FK / IK
- viewer-side qpos pose recompute
- browser-side MuJoCo model loading
- backend runtime large rewrite
- payload schema breaking change
- transport schema breaking change
- legacy import / execute
- package dependency change
- full process manager
- daemon / service 化

## Scope Check

```text
parent issue: #101
depends on: #102, #103
phase slice: R6-G-P3
startup script gap checked: yes
minimal startup helper added or documented unnecessary: yes
host / port / public host args clarified: yes
package dependency added: no
npm dependency added: no
new visual feature added: no
backend runtime rewrite: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
hardware validation included: no
serial port opened: no
OSC sent: no
Rapier reintroduced: no
@types/three reintroduced: no
Closes #104 retained: yes
PR draft retained: yes
```
