---
status: canonical
owner: operations
last_verified: 2026-07-16
canonical_for:
  - WebSocket / host / port / public host contract
  - backend publisher bind host vs browser-visible host
  - WebSocket host and URL contract
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/backend-viewer-startup.md
  - docs/reports/audits/r6-g-p3-startup-script-gap-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
  - docs/operations/websocket-publisher-runner.md
---

# WebSocket / Host / Port Contract

## 目的

backend publisher の bind host / port、browser から見える host、
viewer page URL、WebSocket endpoint URL の関係を 1 か所に固定する。

この文書は host / port / URL の contract を定義するものであり、
production deployment や TLS / reverse proxy / auth の設計は扱わない。

## 用語

### bind host

publisher などが listen する host。

例:

```text
--host 127.0.0.1
--host 0.0.0.0
```

- `127.0.0.1` は同一 machine 内の loopback 接続用。
- `0.0.0.0` は全 interface で listen する bind address。
- `0.0.0.0` は browser から接続する host 名としては通常使わない。

### browser-visible host

browser を実行している端末から見える host。

例:

```text
127.0.0.1
localhost
192.168.x.x
100.x.x.x
example.example.com
```

- local browser なら `127.0.0.1` / `localhost`
- LAN なら LAN IP
- Tailscale なら Tailscale IP / MagicDNS 名
- public host がある場合は public host 名

### WebSocket endpoint URL

browser viewer が payload を受け取る WebSocket URL。

例:

```text
ws://127.0.0.1:8766
ws://192.168.x.x:8766
ws://100.x.x.x:8766
ws://example.example.com:8766
```

### viewer page URL

browser で開く HTML の URL または file path。

例:

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
apps/mujoco-viewer/index.html?ws=ws://127.0.0.1:8766
```

- viewer page URL と WebSocket endpoint URL は別。
- query parameter の `websocketUrl` に WebSocket endpoint URL を入れる。
- `ws` は互換 alias。

## loopback 接続

local browser で同じ machine 上の publisher に接続する最小構成。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
```

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

- browser URL に入れる host は、browser から見える host を使う。
- same machine の browser から見る場合は `127.0.0.1` / `localhost` を使う。
- 別 machine の browser から見る場合は LAN IP / Tailscale IP / public host を使う。
- `localhost` は `127.0.0.1` と同じ loopback の別名として扱う。

## 0.0.0.0 bind

`0.0.0.0` は server 側の bind address であり、browser URL の host ではない。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 0.0.0.0 --port 8766 --steps 3
```

same machine の browser から見る場合:

```text
apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766
```

- server は `0.0.0.0` で listen している。
- same machine の browser からは `127.0.0.1` / `localhost` を使える。
- 別 machine の browser からは `127.0.0.1` ではなく、その browser から見える LAN IP / Tailscale IP / public host を使う。
- `0.0.0.0` を browser URL に入れない。

## LAN 接続

publisher machine と browser machine が同一 LAN にある場合は、browser から見える LAN IP を使う。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 0.0.0.0 --port 8766 --steps 3
```

```text
apps/mujoco-viewer/?websocketUrl=ws://192.168.x.x:8766
```

- `192.168.x.x` は browser から見える publisher machine の LAN IP に置き換える。
- browser page URL と WebSocket endpoint URL は別で、WebSocket 側の host だけを LAN IP にする。

## Tailscale 接続

publisher machine と browser machine が Tailscale 経由でつながる場合は、browser から見える Tailscale IP または MagicDNS 名を使う。

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 0.0.0.0 --port 8766 --steps 3
```

```text
apps/mujoco-viewer/?websocketUrl=ws://100.x.x.x:8766
```

- `100.x.x.x` は browser から見える Tailscale IP に置き換える。
- MagicDNS 名が使えるなら、その名前を `websocketUrl` に入れてよい。

## public host 接続

public host 名が browser から解決でき、かつ publisher がその host で到達可能な場合は、browser から見える public host 名を使う。

```text
apps/mujoco-viewer/?websocketUrl=ws://example.example.com:8766
```

- `0.0.0.0` は public host 名の代わりではない。
- public host / LAN / Tailscale でも、browser から見える host を URL に使う。
- TLS / reverse proxy / auth はこの文書の scope 外であり、ここでは扱わない。

## viewer page URL と WebSocket endpoint URL

viewer page URL は HTML を開く URL、WebSocket endpoint URL は viewer が接続する先の URL である。

```text
viewer page URL:
  apps/mujoco-viewer/?websocketUrl=ws://127.0.0.1:8766

WebSocket endpoint URL:
  ws://127.0.0.1:8766
```

- `websocketUrl` に入れるのは `ws://...` であり、`http://...` ではない。
- backend publisher の port と viewer page の URL は混同しない。
- `ws` は互換 alias だが、正本は `websocketUrl` である。

## よくある混同

- `0.0.0.0` を browser URL に入れる。
- bind host と browser-visible host を同じものとして扱う。
- viewer page URL と WebSocket endpoint URL を混同する。
- backend publisher の port と viewer の page URL を混同する。
- `ws://` と `http://` を混同する。
- LAN / Tailscale / public host で loopback の `127.0.0.1` をそのまま使う。

## Non-Goals

- production deployment
- auth / TLS / reverse proxy
- HTTPS / WSS 対応
- CORS / security policy の本格実装
- hardware / serial / OSC
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- viewer visual feature 追加
- package dependency change
- startup script / wrapper 追加
