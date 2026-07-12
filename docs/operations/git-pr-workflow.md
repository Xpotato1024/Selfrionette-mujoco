---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - git and PR workflow
related:
  - AGENTS.md
---

# Git and PR Workflow

## Branch Hygiene

```bash
git fetch origin
git switch main
git pull --ff-only
git status --short --branch
```

Stop if the working tree is not clean. Codex-created branches use `codex/`.

## PR Diff Gate

Before opening a PR:

```bash
git branch --show-current
git diff --name-only origin/main...HEAD
git diff --check
git status --short --branch
```

Confirm the diff contains only scoped files.

## PR Update Verification

Before reporting an existing PR as updated, verify local HEAD, PR head, and
remote branch HEAD are the same. Also verify the remote branch file content when
the task was wording- or body-sensitive.

## Long-form GitHub body gate

Issue / PRの長文body更新は、write前後で次の2つを独立して検証する。

1. **Transport integrity**: 送信したbodyとAPI read-back bodyが完全一致する。
2. **Structural preservation**: candidateがexact pre-update bodyの見出し、改行、表、code fence、sentinel section、historical ledgerを保持する。

Read-back equality alone is insufficient. A body that was already malformed before transmission can pass exact read-back verification.

numbering SoT、parent Issue、長期roadmap、historical ledgerでは`localized-update`を既定とし、candidateはexact previous bodyへのnarrow replacementまたはpatch applicationで作る。parsed cellsやsummaryから文書全体を再構築しない。

```bash
python scripts/validate_github_body_structure.py before.md after.md \
  --mode localized-update \
  --required-section "## 状態" \
  --required-section "## 更新ルール" \
  --diff-output body-update.diff
```

helperはUTF-8 bodyのbyte length、SHA-256、physical line count、newline count、ordered headings、table delimiter rows、code-fence count、required sentinels、unified diffを比較する。multiline collapse、改行や行数の大幅減少、headingの欠落や並べ替え、table delimiter欠落、unbalanced fence、大領域削除、U+FFFD / mojibake markerを拒否する。CRLFからLFだけの正規化と、構造を保持した小さなrow更新やstatus追記は受理する。

大規模なstructural rewriteはtaskが明示承認した場合に限り、`--allow-structural-change`、空でない`--override-reason`、`--diff-output`をすべて指定する。保存したdiffとoverride reasonを最終報告へ記録する。
