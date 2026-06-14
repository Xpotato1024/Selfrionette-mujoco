---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - R6-G-P1 startup path audit
  - backend / viewer startup path inventory
  - README startup handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/r6-f-completion-audit.md
  - docs/architecture/data-flow.md
---

# R6-G-P1 Startup Path Audit

## 目的

現在の backend / dry-run / Web viewer / browser 接続の起動導線を棚卸しし、
R6-G-P2 以降で README 拡充と起動スクリプト補完を進めるための前提を固定する。
この文書は audit と handoff が目的であり、起動スクリプト実装や viewer 実装の追加はしない。

## 現在の起動導線

現状の導線は loopback 前提の local/dev 経路としては成立している。

- backend / dry-run は `scripts/run_replay_mujoco_dry_run.py`
- WebSocket publisher は `scripts/run_replay_mujoco_websocket_publisher.py`
- browser / viewer smoke は `scripts/run_live_viewer_smoke.py`
- viewer 本体は `apps/mujoco-viewer/index.html` と `dist/browser/main.js`
- browser 接続先は `websocketUrl` query parameter で渡す
- `ws` は互換 alias として受け付ける

## backend / dry-run 起動候補

既存の起動候補は次のとおり。

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --dt-s 0.0166666667
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
```

この導線は replay -> motion -> backend -> payload v0 NDJSON の確認に使える。
WebSocket server も browser も起動しない。

## Web viewer 起動候補

viewer 側の入口は `apps/mujoco-viewer/README.md` と `apps/mujoco-viewer/index.html` にある。

- `npm ci` は browser で `index.html` を直接開く前提条件
- `npm run browser:build` は `dist/browser/main.js` を生成する
- `npm run typecheck` と `npm run build` は TypeScript の静的確認
- `npm test` は viewer runtime / WebSocket skeleton のテスト実行

browser での起動確認は `index.html` を直接開くか、`run_live_viewer_smoke.py` が出力する URL を開く。

## browser 接続候補

browser 側の接続先は明示的な query parameter で渡す。

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

互換 alias は次のとおり。

```text
apps/mujoco-viewer/index.html?ws=ws://127.0.0.1:8766
```

viewer は query が無い場合に自動接続しない。
connection status は DOM 上の summary と分離され、`WebSocket: disabled` / `connecting` / `open` / `closed` / `error` として観測できる。

## WebSocket / host / port の現状

現在の docs と script は loopback の `127.0.0.1:8766` を標準例としている。
`--host` と `--port` は publisher runner と smoke command で指定できるが、`0.0.0.0`・LAN・Tailscale・public host の使い分けはまだ明文化されていない。

現時点で起きやすい混同は次のとおり。

- backend host と browser host を同じものとして扱ってしまう
- bind host と browser から開く URL の host を混同する
- browser page URL と WebSocket URL を混同する
- `localhost` と `127.0.0.1` と `0.0.0.0` の役割差が明文化されていない
- LAN / Tailscale / public host で browser から開く URL の基準がない
- port が埋まっているときの代替 port の決め方がない

## README / docs に既にある記述

- `docs/README.md` は docs SoT map を持っている
- `docs/operations/runtime-dry-run.md` は dry-run コマンドを持っている
- `docs/operations/websocket-publisher-runner.md` は publisher コマンドと endpoint の説明を持っている
- `docs/operations/live-viewer-smoke.md` は CLI 出力の endpoint と browser URL を分離している
- `docs/operations/browser-visual-smoke.md` は root attributes と status text の観測点を持っている
- `apps/mujoco-viewer/README.md` は `websocketUrl` と `ws`、`npm ci`、`browser:build` を説明している
- `docs/architecture/data-flow.md` は replay -> backend -> transport -> viewer の流れを固定している
- `docs/operations/r6-f-completion-audit.md` は viewer visual elements と rendering-only boundary を固定している

## README に不足している項目

現状の README / docs には loopback の最小導線はあるが、次が不足している。

- セットアップの短い全体像
- backend / dry-run の入口一覧
- Web viewer の入口一覧
- browser で開く URL の明示
- WebSocket 接続先の指定方法
- `localhost` と `0.0.0.0` の違い
- bind host と browser URL host の違い
- LAN / Tailscale / public host の見せ方
- port 衝突時の確認方法
- viewer は起動するが payload が来ない場合の確認手順
- browser から public host に接続できない場合の確認手順
- WebSocket URL / host / port の混同回避説明
- R6-F visual elements の smoke 観測方法

## 起動スクリプト不足

### 既存 script で足りているもの

- `scripts/run_replay_mujoco_dry_run.py`
- `scripts/run_replay_mujoco_websocket_publisher.py`
- `scripts/run_live_viewer_smoke.py`
- `npm run browser:build`
- `npm run typecheck`
- `npm run build`
- `npm test`

### README に説明がないだけのもの

- `0.0.0.0` bind と browser URL の分離
- LAN / Tailscale / public host の扱い
- port 衝突時の代替 port 運用
- browser で open にならないときの切り分け
- payload が来ないときの確認手順

### script / npm script / wrapper が不足しているもの

- Windows / PowerShell 向けの短い起動ラッパー
- `0.0.0.0` bind と browser URL を同時に案内する補助 wrapper
- public host / LAN / Tailscale で使う browser URL を明示生成する補助

### R6-G-P3 で実装または補完すべきもの

- README で loopback / browser URL / WebSocket URL を分けて説明する
- 必要なら Windows / PowerShell 向けの短い wrapper を追加する
- 必要なら `0.0.0.0` / LAN / Tailscale / public host の URL 案内を追加する

### R6-G-P3 で「不足なし」と判断できるもの

loopback 前提の現行導線そのものは不足していない。
不足しているのは主に説明と見せ方であり、少なくとも現時点では startup script 実装は必須ではない。

## R6-G-P2 への handoff

- README の最初のページで、backend / dry-run / publisher / viewer / browser URL を短く並べる
- `websocketUrl` と `ws` の違いを明示する
- `browser URL` と `WebSocket URL` を別概念として説明する
- `npm ci` / `browser:build` / `typecheck` / `build` / `test` の役割を分ける
- ループバックの例と、それ以外の host の例を分けて書く

## R6-G-P3 への handoff

- `0.0.0.0` bind と browser URL host の違いを README / docs で補完する
- Windows / PowerShell 向けの導線が必要か判断する
- port 衝突時の具体的な運用を書けるなら、wrapper か README のどちらかで固定する
- browser から payload が来ない場合の切り分けを手順化する

## R6-G-P4 への handoff

- LAN / Tailscale / public host での接続可否を確認できる形にする
- browser URL の host が bind host と一致しないケースを説明する
- root attributes と status text の観測で smoke 成否を判定する

## R6-G-P5 への handoff

- ここまでの README / docs / wrapper の整備結果を再 audit して freeze する
- 起動導線の説明と実際のスクリプトの差分が残っていないかを確認する
- `docs/operations/browser-visual-smoke.md` と `docs/operations/r6-f-completion-audit.md` への参照が、現行導線と矛盾していないかを確認する

## Non-Goals

- 起動スクリプトの実装
- npm script の追加
- backend runtime の大改造
- viewer visual feature の追加
- viewer-side FK / IK
- viewer-side qpos pose recompute
- browser-side MuJoCo model loading
- production deployment
- auth / TLS / reverse proxy
- hardware validation
- serial port open
- OSC send
- legacy import / execute / direct migration
- payload schema breaking change
- transport schema breaking change
- package dependency change
- Rapier reintroduction
- `@types/three` reintroduction

## Scope Check

```text
parent issue: #101
phase slice: R6-G-P1
startup path audit added: yes
README gaps listed: yes
script gaps listed: yes
host / port / WebSocket ambiguity listed: yes
new visual feature added: no
startup script implemented: no
legacy changed: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
payload schema breaking change: no
transport schema breaking change: no
hardware validation included: no
serial port opened: no
OSC sent: no
Rapier reintroduced: no
@types/three reintroduced: no
```
