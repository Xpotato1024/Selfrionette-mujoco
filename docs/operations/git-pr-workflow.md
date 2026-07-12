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

before / after input bodyは別のfilesystem objectでなければならない。同一path、absolute / relative alias、symlink、hardlink、Windows case aliasはdecode前のresolved / same-file gateでhard failureとして拒否する。別fileに保存された同一bytesはno-op updateとして受理できる。

helperはMarkdownを1回走査し、fenced code blockの内外を追跡する。heading、table block、required sentinel headingはfence外だけから抽出し、code sample内の同一文字列を文書構造として扱わない。required sentinelはfence外のexact heading lineでなければならない。

numbering SoTとparent / roadmap Issueには`--profile protected-long-form`を使用し、対象ごとの`--required-section`を明示する。tableを持つprofileでは`--required-table-section`でheadingに紐づくtable identityも指定する。このprofileはbefore bodyのmultiline baseline、実heading、required sentinel、required table identityをwrite前に検証する。1 physical line上の複数heading marker、parsed headingが0のまま複数heading-like fragmentを含むbody、collapsed before、sentinel / table identity欠落はhard failureであり、candidateも同様にcollapsedしているかどうかに関係なく通常のlocalized updateを停止する。既知正常multiline backup、damaged latest evidence、repair candidateによるrecovery workflowを使用し、overrideでbaseline failureを回避しない。

GFM tableはtop-levelのheader-plus-delimiter blockとして検証する。delimiterは直前の非blank pipe-separated headerと隣接し、effective column countが一致する場合だけ登録する。leading / trailing pipeは任意で、delimiter cellは空白を除いてoptional leading colon、3個以上のhyphen、optional trailing colonだけを許可する。ordered blockにはnearest preceding heading、column count、alignment tuple、raw header / delimiterを保持する。delimiter-like text単体、blank lineでheaderから離れたdelimiter、別位置へ移動したdelimiter、indented/fenced code、column mismatchはtableとして数えず、既存tableを壊す変更はstructural violationとして拒否する。

localized updateではordered fence block structureとしてmarker typeとopening lengthを比較する。code block本文の通常編集は許可するが、block数、順序、backtick / tilde種別、opening lengthの変更はstructural violationとする。unbalanced / mismatched fenceはhard failureである。

### Failure classes and structural override

hard failureはoverrideできない。対象はunreadable / non-UTF-8 / BOM input、empty body、multilineからone-lineへのcollapse、U+FFFD・既知mojibake・`???`などのreplacement marker、unbalancedまたはmismatched fence、無効なoverride reason、required diff evidenceの保存失敗である。一方、headingの削除・並べ替え、table変更、balanced fence削除、valid multilineを保つ大規模section置換やline/newline削減はstructural violationとして分類する。

大規模なstructural rewriteはtaskが明示承認した場合に限り、`--allow-structural-change`、空でない`--override-reason`、`--diff-output`をすべて指定する。overrideはstructural violationが実在し、hard failureがなく、保存diffのexact read-backに成功した場合だけ有効になる。通常検証が通るcandidateでは`override_used=false`のままとする。imported Python APIでも`validate()`単体はoverride不能で、`apply_structural_override()`へreasonとdiff evidence pathを渡す同じgateを使用する。diff evidence pathはabsolute / resolved pathと可能な場合はsame-file検査を行い、before / after body自身、relative alias、symlink aliasへの書込みをhard failureとして拒否する。保存したdiffとoverride reasonを最終報告へ記録する。

### Older-backup recovery reconciliation

古い正常multiline backupから長期bodyを復旧するときは、そのbackupだけを採用して完了しない。damaged latest bodyは構造sourceにせずcontent evidenceとして扱い、known-good backup / damaged latest body / repair candidateをLF-normalized、whitespace-normalized token、heading、table row、ledger entryで三者比較する。damaged latest bodyだけに存在するmaterial fragmentをhistorical entry、superseded metadata、duplicated/corrupted fragment、formatting-only artifact、unresolvedへ分類し、正当な後続historyだけを構造を保って追記する。machine-readable reportとhuman-readable diffはrepository外へ保存する。
