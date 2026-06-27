---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - MuJoCo viewer dev launcher
  - AutoPort startup helper
  - Tailscale / LAN / public host viewer URL helper
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/websocket-host-port-contract.md
  - docs/operations/runtime-to-viewer-e2e-smoke.md
---

# MuJoCo Viewer Dev Launcher

## 目的

runtime-to-viewer E2E smoke を再現しやすくするための dev-only 補助です。
browser を強制 open せず、bind host と browser-visible host を分けて URL を
表示します。

## 対象

- backend publisher の bind host / port
- browser から見える WebSocket endpoint URL
- browser page URL
- AutoPort による port 自動選択
- `npm run browser:build` の実行可否

## CLI

```bash
uv run python scripts/run_mujoco_viewer_dev.py --host 127.0.0.1 --port 8766 --steps 3 --preset sweep_x
uv run python scripts/run_mujoco_viewer_dev.py --host 0.0.0.0 --port 8766 --auto-port --public-host 100.x.x.x --steps 3 --preset sweep_x
uv run python scripts/run_mujoco_viewer_dev.py --print-only --no-browser-build
```

## AutoPort

- `--auto-port` がない場合は、要求 port が使用中なら error で止めます。
- `--auto-port` がある場合は、要求 port 以降の空き port を選びます。
- 選ばれた port は stdout に明示します。

## loopback

同一 machine で browser を開く場合は `127.0.0.1` を案内します。
`localhost` も loopback として扱います。

## 0.0.0.0 bind

`0.0.0.0` は bind address であり、browser URL の host ではありません。
`--host 0.0.0.0` のときでも、`--public-host` がなければ browser-visible host は
`127.0.0.1` にします。

## LAN / Tailscale / public host

LAN / Tailscale / public host から開く場合は `--public-host` を明示します。
launcher は browser page URL と WebSocket endpoint URL の両方を表示します。

## print-only mode

`--print-only` は subprocess を起動しません。URL と command だけを表示します。
`--print-only` と `--no-browser-build` を併用すると、完全に表示専用になります。

## browser build

`--no-browser-build` がない場合、launcher は `cd apps/mujoco-viewer && npm run browser:build`
を実行します。browser は自動 open しません。

## examples

### loopback

```text
Selected WebSocket publisher:
  bind:   127.0.0.1:8766
  browser host: 127.0.0.1
  websocket: ws://127.0.0.1:8766

Open viewer:
  apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

### Tailscale / LAN

```text
Selected WebSocket publisher:
  bind:   0.0.0.0:8766
  browser host: 100.x.x.x
  websocket: ws://100.x.x.x:8766

Open viewer:
  apps/mujoco-viewer/?websocketUrl=ws://100.x.x.x:8766
```

## R6-G-P7 への handoff

- R6-G-P7 では、P1〜P6 の completion state を audit する。
- AutoPort / one-command / Tailscale WebView dev launcher の completion state を確認する。
- README / viewer README / operations docs から launcher docs に辿れることを確認する。
- parent #101 を close できる completion audit を追加する。

## Non-Goals

- production server
- auth / TLS / reverse proxy
- HTTPS / WSS
- browser を強制 open
- full process manager
- daemon / service 化
- hardware / serial / OSC
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- viewer visual feature 追加
- package dependency change
- legacy import / execute / direct migration

## Scope Check

```text
dev launcher added: yes
AutoPort implemented: yes
browser-visible host separated: yes
viewer page URL output documented: yes
WebSocket endpoint URL output documented: yes
print-only mode documented: yes
browser build documented: yes
browser auto open: no
production deployment added: no
auth / TLS / reverse proxy added: no
hardware validation included: no
serial port opened: no
OSC sent: no
legacy imported/executed: no
viewer-side FK/IK added: no
viewer-side qpos recompute added: no
browser-side MuJoCo model loading added: no
package dependency changed: no
Closes #113 retained: yes
PR draft retained: yes
```
