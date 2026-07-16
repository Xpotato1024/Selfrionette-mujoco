---
status: historical
owner: operations
last_verified: 2026-06-22
canonical_for: []
related:
  - docs/README.md
  - docs/operations/hardware-safety.md
  - docs/operations/validation.md
  - docs/operations/japanese-doc-writing-guardrails.md
---

# R7-C manual validation preflight

## 目的

この文書は、R7-C の manual validation に入る前の事前確認を固定する。
ここで扱うのは preflight だけであり、実機の live 手順や serial 接続そのものは扱わない。
後続の child 手順で manual live serial が必要になった場合でも、この文書の範囲外で実施する。

## pre-run checklist

- issue #232 の対象 scope が docs-only であることを確認する
- branch が `codex/232-r7-c-manual-validation-preflight` であることを確認する
- `main` から作成した最新 branch であることを確認する
- `docs/README.md` の SoT map に本書が載っていることを確認する
- `tests/architecture/test_docs_sot.py` が本書を canonical doc として認識することを確認する
- 変更対象が許可された 3 ファイルだけであることを確認する
- `MUJOCO_LOG.TXT` を含む実行ログや生成物を追加しない
- serial port, OSC, browser, WebSocket, hardware validation をここでは実行しない

## 必要な local prerequisites

- Git と `uv` が利用できること
- `docs/` 配下を UTF-8 without BOM で扱えること
- PowerShell で Markdown を書き換えた場合は mojibake / BOM を確認できること
- repo の docs SoT ルールを読み終えていること

## no-robot-output safety statement

この preflight は robot output を一切出さない。
serial port を開かない、OSC を送らない、hardware を動かさない、browser や WebSocket を起動しない。
MuJoCo backend, runtime, transport, viewer の実装や検証にも進まない。

## manual live serial は後続 child 手順のみ

manual live serial の取り扱いは、後続の child 手順に限定する。
この文書では live serial の接続方法、port 指定、受信フロー、実機確認は定義しない。
必要になった場合は、`#235` の live loadcell validation log 手順で manual gate と
stop 条件を明示してから扱う。

## validation command list

この issue で扱う検証は docs-only validation だけに限定する。

```powershell
git diff --check
uv run pytest tests/architecture/test_docs_sot.py
```

日本語 docs を編集したため、encoding / mojibake check も必ず行う。

```powershell
@'
from pathlib import Path

paths = [
    "AGENTS.md",
    "docs/README.md",
    "docs/operations/r7-c-manual-validation-preflight.md",
]

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
    data = Path(p).read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise SystemExit(f"BOM remains: {p}")
    text = data.decode("utf-8")
    found = [token for token in bad_tokens if token in text]
    if found:
        raise SystemExit(f"mojibake-like tokens remain in {p}: {found}")

print("Japanese docs encoding check passed")
'@ | uv run python -
```

## artifact / log storage policy

- この issue では新しい log file を repo に追加しない
- 実行結果は terminal と issue / PR で共有し、恒久保存が必要な場合のみ後続 issue の指示に従う
- 生成物を残す場合も `MUJOCO_LOG.TXT` を流用しない
- ここで扱う証跡は docs-only の範囲に限定する

## known limitations

- この文書だけでは manual live serial は完了しない
- 実機確認、serial 受信、OSC、browser、WebSocket、MuJoCo 実行は未実施のままである
- later child 手順の安全条件や stop 条件は、child 側の文書で別途固定する

## handoff

次は `#233` で viewer launch と fixture demo procedure を整備する。
manual live serial は `#235` 以降の manual-gated 手順で扱い、本書はその前段の
preflight と docs SoT の固定までを担当する。
