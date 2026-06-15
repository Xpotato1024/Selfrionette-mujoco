---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - R6-G completion audit
  - backend / viewer startup completion
  - runtime-to-viewer E2E smoke completion
  - Phase G parent close handoff
related:
  - README.md
  - apps/mujoco-viewer/README.md
  - docs/operations/r6-g-p1-startup-path-audit.md
  - docs/operations/backend-viewer-startup.md
  - docs/operations/r6-g-p3-startup-script-gap-audit.md
  - docs/operations/websocket-host-port-contract.md
  - docs/operations/runtime-to-viewer-e2e-smoke.md
  - docs/operations/mujoco-viewer-dev-launcher.md
---

# R6-G Completion Audit

## 目的

R6-G で整備した backend / dry-run / WebSocket publisher / Web viewer /
browser 接続導線、README、起動スクリプト補完判断、WebSocket / host / port
contract、runtime-to-viewer E2E smoke、AutoPort / one-command / Tailscale
WebView dev launcher の completion state を docs に固定し、parent #101 を
completed close できる状態にする。

この文書は completion audit と parent close handoff であり、新規 feature 実装ではない。

## Parent issue

- #101

## Child issues

- #102: R6-G-P1 startup path audit
- #103: R6-G-P2 README / backend-viewer startup guide
- #104: R6-G-P3 startup script gap audit
- #105: R6-G-P4 WebSocket / host / port contract
- #106: R6-G-P5 runtime-to-viewer E2E smoke / troubleshooting
- #113: R6-G-P6 AutoPort / one-command / Tailscale WebView dev launcher
- #107: R6-G-P7 Phase G completion audit

## Completion summary

R6-G では、backend / dry-run / WebSocket publisher / Web viewer / browser
接続までの導線を、README / operations docs / dev launcher で再現可能な状態にした。

主な completion state:

- startup path audit 完了
- README / viewer README から起動導線へ到達可能
- backend-viewer startup guide 追加済み
- script gap は確認済み
- WebSocket / host / port / public host contract 追加済み
- runtime-to-viewer E2E smoke / troubleshooting 追加済み
- AutoPort / one-command / Tailscale WebView dev launcher 追加済み
- 日本語 docs / PR body guardrail 追加済み

## Startup path completion

- #102 で現在の backend / viewer 起動導線を audit し、README gaps と script gaps を
  分離した。
- #103 で backend / dry-run / Web viewer / browser 接続手順を README と viewer README
  へ固定した。
- browser-visible host と bind host の違いは docs 側で明文化済みである。

## README / docs completion

- `README.md` から backend / dry-run / WebSocket publisher / Web viewer / browser
  接続導線へ辿れる。
- `apps/mujoco-viewer/README.md` から `websocketUrl` / `ws` / `browser:build` /
  `mujoco-viewer-dev-launcher.md` に辿れる。
- `docs/README.md` の Source of Truth Map から R6-G の operation docs 群へ辿れる。
- `docs/architecture/data-flow.md` と docs/operations 群の間で、viewer は
  rendering-only であるという boundary が維持されている。

## Script gap completion

- #104 で起動スクリプトの不足は最小補完済みである。
- #113 で AutoPort / one-command / Tailscale WebView dev launcher が追加済みである。
- P7 では新しい起動 helper を追加しない。
- script gap の結論は「不足なし」ではなく、「必要最小限の thin helper は既に揃っている」
  で固定する。

## WebSocket / host / port contract completion

- #105 で bind host、browser-visible host、viewer page URL、WebSocket endpoint URL の
  contract が固定された。
- `localhost` / `127.0.0.1` / `0.0.0.0` の役割分担が明文化されている。
- LAN / Tailscale / public host は browser-visible host として扱い、bind host とは分離する。
- production deployment、auth、TLS、reverse proxy は scope 外のままである。

## Runtime-to-viewer E2E smoke completion

- #106 で backend / dry-run から viewer / browser までの smoke と troubleshooting が
  文書化された。
- root attributes と status text による観測点が整理された。
- target / tip / error / skeleton / mesh / DoF ring の観測手順が固定された。
- browser console の WebSocket error、port 衝突、URL 混同の切り分けが追加済みである。

## AutoPort / WebView dev launcher completion

- #113 で AutoPort、one-command、Tailscale WebView dev launcher の completion state が
  固定された。
- launcher は production process manager ではない。
- browser は自動 open しない。
- viewer page URL と WebSocket endpoint URL は launcher 出力で確認できる。

## Rendering-only viewer confirmation

- viewer は rendering-only のままである。
- viewer-side FK / IK は導入していない。
- viewer-side qpos pose recompute は導入していない。
- browser-side MuJoCo model loading は導入していない。
- viewer は MuJoCo backend を import しない。
- viewer は transport payload v0 を観測するだけで、state source of truth にはならない。

## Out-of-scope confirmation

R6-G では以下を行っていない。

- production deployment
- auth / TLS / reverse proxy
- hardware validation
- serial port open
- OSC send
- browser-side MuJoCo model loading
- viewer-side FK / IK
- viewer-side qpos pose recompute
- viewer visual feature 追加
- payload schema breaking change
- transport schema breaking change
- package dependency change
- legacy import / execute / direct migration

## Remaining risks

- dev launcher は production process manager ではない
- browser は自動 open しない
- publisher process は launcher から自動管理しない
- Tailscale / LAN 接続は OS firewall / network permission の影響を受ける
- WebSocket URL / viewer page URL の指定ミスは引き続き troubleshooting 対象

## Next phase handoff

R6-G は起動導線と E2E smoke の整備を完了した。
次 phase では、runtime / backend / viewer の実機能拡張や、MuJoCo state /
command integration の次段に進める。

次 phase で扱う候補:

- runtime / MuJoCo backend integration の拡張
- viewer payload observation の追加整理
- 操作入力から command / target / qpos への接続
- smoke ではなく実操作に近い replay / input flow の確認

## Parent close handoff

この PR merge 後、#101 parent issue に completion comment を追加し、completed
として close する。

推奨 parent comment:

```markdown
R6-G の child issues が完了しました。

完了した範囲:

- #102: startup path audit
- #103: README / backend-viewer startup guide
- #104: startup script gap audit
- #105: WebSocket / host / port contract
- #106: runtime-to-viewer E2E smoke / troubleshooting
- #113: AutoPort / one-command / Tailscale WebView dev launcher
- #107: Phase G completion audit

主な成果:

- backend / dry-run / WebSocket publisher / Web viewer / browser 接続導線を docs に固定
- README / viewer README / operations docs から再現手順へ到達可能
- host / port / browser-visible host / WebSocket endpoint URL の contract を固定
- runtime-to-viewer E2E smoke と troubleshooting を追加
- AutoPort / one-command / Tailscale WebView dev launcher を追加
- 日本語 docs / PR body guardrail を追加

R6-G parent は完了として close します。
```

## Validation

docs-only validation:

```bash
git diff --check
```

日本語 docs encoding check:

```bash
python - <<'PY'
from pathlib import Path

paths = [
    "README.md",
    "AGENTS.md",
    "apps/mujoco-viewer/README.md",
    "docs/README.md",
]

paths.extend(str(p) for p in Path("docs").rglob("*.md"))

bad_tokens = [
    "\u7e3a",
    "\u7e67",
    "\u8700",
    "\u9aea",
    "\u8b17",
    "\u9036",
    "\u8b5b",
    "\u83a0",
    "\u7e32",
    "\u0080",
]

for p in paths:
    path = Path(p)
    if not path.exists():
        continue

    data = path.read_bytes()

    if data.startswith(b"\xef\xbb\xbf"):
        raise SystemExit(f"BOM remains: {p}")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"not UTF-8: {p}: {exc}") from exc

    found = [token for token in bad_tokens if token in text]
    if found:
        raise SystemExit(f"mojibake-like tokens remain in {p}: {found}")

print("Japanese docs encoding check passed")
PY
```

PR body check:

```bash
gh pr view <PR_NUMBER> --json body --jq '.body' | python - <<'PY'
import sys

body = sys.stdin.read()

if body.startswith("\ufeff"):
    raise SystemExit("PR body starts with BOM")

bad_tokens = [
    "\u7e3a",
    "\u7e67",
    "\u8700",
    "\u9aea",
    "\u8b17",
    "\u9036",
    "\u8b5b",
    "\u83a0",
    "\u7e32",
    "\u0080",
]

found = [token for token in bad_tokens if token in body]
if found:
    raise SystemExit(f"PR body mojibake-like tokens remain: {found}")

if "Closes #107" not in body:
    raise SystemExit("Closes #107 missing")

print("PR body encoding check passed")
PY
```

placeholder 残存 check:

```bash
python - <<'PY'
from pathlib import Path

paths = [
    "AGENTS.md",
    "docs/operations/japanese-doc-writing-guardrails.md",
]

bad_placeholders = [
    "MOJIBAKE_TOKEN_1",
    "MOJIBAKE_TOKEN_2",
    "MOJIBAKE_TOKEN_3",
]

for p in paths:
    text = Path(p).read_text(encoding="utf-8")
    found = [token for token in bad_placeholders if token in text]
    if found:
        raise SystemExit(f"placeholder mojibake tokens remain in {p}: {found}")

print("placeholder check passed")
PY
```

## Scope Check

```text
parent issue: #101
depends on: #102, #103, #104, #105, #106, #113
phase slice: R6-G-P7
Phase G completion audit added: yes
completed child issues checked: yes
README startup guide completion documented: yes
startup script completion documented: yes
WebSocket / host / port contract completion documented: yes
runtime-to-viewer E2E smoke documented: yes
autoport / one-command / Tailscale WebView completion documented: yes
parent closure handoff added: yes
new visual feature added: no
startup script implementation added in this issue: no
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
docs / SoT impact checked: yes
```
