---
status: canonical
owner: operations
last_verified: 2026-06-15
canonical_for:
  - Japanese docs writing guardrails
  - UTF-8 / BOM / mojibake prevention
  - PR body Japanese formatting checks
related:
  - AGENTS.md
  - README.md
  - docs/README.md
  - docs/operations/backend-viewer-startup.md
---

# Japanese Docs Writing Guardrails

## 目的

日本語 docs と PR body の文字化け、BOM 混入、handoff ずれを防ぐ。

## 発生した問題

今回の backend / viewer startup guide では、Windows / PowerShell 経由の書き込みと再生成の過程で、Markdown 本文が mojibake 化した。
さらに、PR body の先頭 BOM や、日本語 docs に不要な英語文が残る差戻しも繰り返し発生している。

## 推定原因

今回の mojibake は、UTF-8 で扱うべき Markdown 本文が、Windows / PowerShell / terminal / clipboard / redirection / file write のどこかで CP932 / Shift-JIS 相当として扱われた、または CP932 相当の文字列を UTF-8 として再解釈した可能性が高い。

再発防止のため、原因を単一の操作に限定せず、以下を guardrail として扱う。

- Markdown は UTF-8 without BOM で保存する
- PR body の先頭に BOM を入れない
- 日本語本文を terminal から再生成する場合は、保存後に mojibake token check を必ず実行する
- Windows / PowerShell 経由で日本語 Markdown を生成・追記・置換した場合は、必ず BOM check と mojibake check を実行する
- `git diff --check` だけでは文字化けを検出できないため、別途 text encoding check を行う

## 必須ルール

- docs / README / PR body の日本語は UTF-8 without BOM とする
- docs に日本語を追加・更新した場合、mojibake token check を実行する
- PR body を作成・更新した場合、先頭 BOM がないことを確認する
- `git diff --check` は whitespace check であり、文字化け検出ではない
- 日本語 docs の review では、内容だけでなく encoding / mojibake / BOM を必ず確認する
- docs に英語文を残す場合は、CLI option / API field / code / filename / proper noun など必要な箇所に限る
- issue / PR / docs の handoff は、実際に存在する child issue 番号・scope と一致させる

## 禁止事項

- mojibake を含む Markdown を commit しない
- PR body を `\ufeff## Summary` で始めない
- 日本語 docs の本文を CP932 / Shift-JIS 前提で保存しない
- PowerShell の既定 encoding に依存して日本語 Markdown を生成しない
- `git diff --check passed` だけをもって日本語 docs の品質確認完了としない

## PR body ルール

PR body は GitHub metadata なので file check では検出できない。
PR 作成・更新後に body を読み出し、先頭 BOM と mojibake token を確認する。

## Markdown docs ルール

Markdown を書き換えた後は、テキスト本文に mojibake token が残っていないかを確認する。
必要な英語は CLI option / API field / code / filename / proper noun に限定する。

## 検証コマンド

```bash
git diff --check
```

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
    "\u7e3a",  # common mojibake token 1
    "\u7e67",  # common mojibake token 2
    "\u8700",  # common mojibake token 3
    "\u9aea",  # common mojibake token 4
    "\u8b17",  # common mojibake token 5
    "\u9036",  # common mojibake token 6
    "\u8b5b",  # common mojibake token 7
    "\u83a0",  # common mojibake token 8
    "\u7e32",  # common mojibake token 9
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

## mojibake token check

mojibake token は raw 文字で Markdown 本文に直書きしない。
ただし、検証コマンドでは unicode escape で検出対象を定義し、実行時に実際の mojibake を検出できるようにする。

placeholder だけの検証は禁止する。

## BOM check

PR body は先頭 BOM なしで作成する。必要なら `gh pr view` で body を取り出して確認する。

## 日本語文体 check

- 日本語 docs は簡潔に書く
- handoff は実際の issue / scope に一致させる
- 英語を残す場合は必要最小限にする

## Codex / agent handoff ルール

- docs-only issue では runtime / viewer feature を追加しない
- 起動スクリプト補完 issue では package dependency を増やさない
- viewer は rendering-only を維持する
- viewer-side FK / IK / qpos recompute を追加しない
- browser-side MuJoCo model loading を追加しない
- hardware / serial / OSC は明示許可がない限り扱わない

## Scope Check

```text
Japanese docs guardrails added: yes
UTF-8 without BOM policy added: yes
mojibake prevention added: yes
PR body guardrail added: yes
encoding check command added: yes
diff check command added: yes
scope discipline added: yes
```
