---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - backend / viewer startup guide
  - browser WebSocket connection guide
  - R6-G-P2 README startup handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/r6-g-p1-startup-path-audit.md
  - docs/operations/browser-visual-smoke.md
  - docs/operations/live-viewer-smoke.md
---

# Backend / Viewer Startup Guide

## 逶ｮ逧・
backend / dry-run / WebSocket publisher / Web viewer / browser 謗･邯壹・蟆守ｷ壹ｒ 1 縺区園縺ｫ蝗ｺ螳壹☆繧九・R6-G-P2 縺ｮ README 諡｡蜈・・縲√％縺ｮ謇矩・∈縺ｮ譯亥・縺縺代ｒ諡・＞縲∬ｵｷ蜍輔せ繧ｯ繝ｪ繝励ヨ縺ｮ霑ｽ蜉繧・viewer 讖溯・縺ｮ霑ｽ蜉縺ｯ陦後ｏ縺ｪ縺・・
## 繧ｻ繝・ヨ繧｢繝・・

- Python 蛛ｴ縺ｯ `uv run ...` 繧剃ｽｿ縺・・- viewer 蛛ｴ縺ｯ `apps/mujoco-viewer` 驟堺ｸ九〒 `npm ci` 繧貞ｮ溯｡後☆繧九・- browser viewer 逕ｨ縺ｫ `npm run browser:build` 繧貞ｮ溯｡後☆繧九・- `npm run typecheck` 縺ｨ `npm run build` 縺ｯ TypeScript 縺ｮ髱咏噪讀懆ｨｼ縲・- `npm test` 縺ｯ viewer runtime / WebSocket skeleton 縺ｮ繝・せ繝医・
## 譛遏ｭ loopback 謇矩・
1. backend 縺ｮ dry-run 縺ｧ payload / backend path 繧堤｢ｺ隱阪☆繧九・2. WebSocket publisher 繧・`127.0.0.1:8766` 縺ｧ襍ｷ蜍輔☆繧九・3. viewer 繧・browser 逕ｨ縺ｫ build 縺吶ｋ縲・4. browser 縺ｧ viewer page URL 繧帝幕縺阪～websocketUrl` 繧呈欠螳壹☆繧九・5. viewer 縺ｮ status / root attributes 縺ｧ謗･邯夂憾諷九ｒ隕ｳ貂ｬ縺吶ｋ縲・
## backend / dry-run

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --preset sweep_x
```

- dry-run 縺ｯ NDJSON payload / backend path 縺ｮ遒ｺ隱咲畑縲・- WebSocket server 縺ｯ襍ｷ蜍輔＠縺ｪ縺・・- browser viewer 縺ｨ縺ｯ逶ｴ謗･謗･邯壹＠縺ｪ縺・・- `sweep_x` 縺ｯ R6-F visual demo 縺ｮ deterministic replay fixture縲・
## WebSocket publisher

```bash
uv run python scripts/run_replay_mujoco_websocket_publisher.py --host 127.0.0.1 --port 8766 --steps 3
```

- browser viewer 縺ｫ payload v0 繧呈ｵ√☆ local/dev publisher縲・- 讓呎ｺ也噪縺ｪ loopback 縺ｯ `127.0.0.1:8766`縲・- `--host` 縺ｯ bind host縲・- `--port` 縺ｯ WebSocket endpoint port縲・- `--steps` 縺ｯ replay step 謨ｰ縲・- publisher 縺ｯ browser page 繧帝幕縺九↑縺・・
## Web viewer

```bash
cd apps/mujoco-viewer
npm ci
npm run browser:build
```

browser 縺ｧ髢九￥ URL 萓・

```text
apps/mujoco-viewer/index.html?websocketUrl=ws://127.0.0.1:8766
```

莠呈鋤 alias:

```text
apps/mujoco-viewer/index.html?ws=ws://127.0.0.1:8766
```

- browser page URL 縺ｨ WebSocket URL 縺ｯ蛻･讎ょｿｵ縲・- viewer 縺ｯ `websocketUrl` 繧貞━蜈医＠縲～ws` 縺ｯ莠呈鋤 alias縲・- query 縺後↑縺・ｴ蜷医・閾ｪ蜍墓磁邯壹＠縺ｪ縺・・- WebSocket status 縺ｯ viewer 荳翫・ status / root attributes 縺ｧ隕ｳ貂ｬ縺吶ｋ縲・- `npm run browser:build` 縺ｯ `index.html` 縺瑚ｪｭ繧 `dist/browser/main.js` 繧剃ｽ懊ｋ縲・
## localhost / 127.0.0.1 / 0.0.0.0

```text
127.0.0.1 / localhost:
  蜷後§ machine 荳翫・ browser 縺九ｉ謗･邯壹☆繧・loopback 逕ｨ

0.0.0.0:
  server 縺悟・ interface 縺ｧ listen 縺吶ｋ縺溘ａ縺ｮ bind address
  browser 縺ｧ髢九￥ URL 縺ｮ host 縺ｨ縺励※縺ｯ騾壼ｸｸ菴ｿ繧上↑縺・
LAN / Tailscale / public host:
  browser 蛛ｴ縺ｮ URL / WebSocket URL 縺ｫ縺ｯ縲｜rowser 縺九ｉ隕九∴繧・host 繧剃ｽｿ縺・```

- `0.0.0.0` 縺ｧ bind 縺励※繧ゅ｜rowser 縺九ｉ縺ｯ `127.0.0.1` / LAN IP / Tailscale IP 縺ｪ縺ｩ縺ｧ謗･邯壹☆繧九・- bind host 縺ｨ browser 縺九ｉ隕九∴繧・host 縺ｯ蛻･縲・
## port / URL 縺ｮ豺ｷ蜷悟屓驕ｿ

- viewer page URL 縺ｨ WebSocket endpoint URL 縺ｯ蛻･縲・- viewer host / port 縺ｨ backend publisher host / port 縺ｯ蛻･縲・- bind host 縺ｨ browser 縺九ｉ隕九∴繧・host 縺ｯ蛻･縲・- `0.0.0.0` 繧・browser URL 縺ｫ蜈･繧後↑縺・・- port 縺悟沂縺ｾ縺｣縺ｦ縺・ｋ蝣ｴ蜷医・蛻･ port 繧剃ｽｿ縺・°縲∵里蟄倥・繝ｭ繧ｻ繧ｹ繧呈ｭ｢繧√ｋ縲・
## R6-F visual elements 縺ｮ隕ｳ貂ｬ

- browser smoke 縺ｯ target / tip / error vector / arm skeleton / fast_arm mesh / DoF ring 縺ｮ隕ｳ貂ｬ蜈･蜿｣縲・- 縺ｾ縺・status text 縺ｨ root attributes 繧堤｢ｺ隱阪☆繧九・- 縺昴・蠕後［arker summary 縺ｨ counts 縺・payload v0 縺ｫ霑ｽ髫上☆繧九°繧定ｦ九ｋ縲・- payload 縺梧擂縺ｪ縺・ｴ蜷医・縲｝ublisher 縺ｨ browser URL 縺ｮ host / port / endpoint 繧定ｦ狗峩縺吶・
## Troubleshooting 蜈･蜿｣

- port 縺悟沂縺ｾ縺｣縺ｦ縺・ｋ縲・- viewer 縺ｯ髢九￥縺・payload 縺梧擂縺ｪ縺・・- WebSocket status 縺・`open` 縺ｫ縺ｪ繧峨↑縺・・- LAN / Tailscale 縺九ｉ謗･邯壹〒縺阪↑縺・・- browser page URL 縺ｨ WebSocket URL 繧呈ｷｷ蜷後＠縺ｦ縺・ｋ縲・- `0.0.0.0` 繧・browser URL 縺ｫ蜈･繧後※縺・ｋ縲・
隧ｳ邏ｰ縺ｪ蛻・ｊ蛻・￠縺ｯ `docs/operations/browser-visual-smoke.md` 縺ｨ `docs/operations/live-viewer-smoke.md` 繧貞盾辣ｧ縺吶ｋ縲・蠢・ｦ√↑繧・#106 / R6-G-P5 縺ｧ troubleshooting 繧呈僑蜈・☆繧九・
## R6-G-P3 縺ｸ縺ｮ handoff

- R6-G-P2 では起動スクリプトや npm script は追加しない。
- R6-G-P3 では、この README / docs 導線を実行するうえで script / wrapper / npm script の不足が残るかを確認する。
- 不足が説明だけで解消できる場合は、script を追加せず docs に「不足なし」と固定する。
- Windows / PowerShell 向けの短い wrapper、`0.0.0.0` bind と browser URL を同時に案内する補助、public host / LAN / Tailscale 向け URL 案内補助が必要な場合のみ、R6-G-P3 で最小補完する。
- package dependency は追加しない。
- viewer visual feature は追加しない。
## Non-Goals

- 襍ｷ蜍輔せ繧ｯ繝ｪ繝励ヨ縺ｮ螳溯｣・- npm script 縺ｮ霑ｽ蜉
- package dependency change
- backend runtime 縺ｮ螟ｧ謾ｹ騾
- viewer visual feature 霑ｽ蜉
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
- Rapier reintroduction
- `@types/three` reintroduction

## Scope Check

```text
parent issue: #101
depends on: #102
phase slice: R6-G-P2
README startup guide added: yes
backend / dry-run startup documented: yes
viewer startup documented: yes
browser connection documented: yes
WebSocket URL documented: yes
localhost / 0.0.0.0 / public host documented: yes
R6-F visual smoke observation documented: yes
startup script implemented: no
new visual feature added: no
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
