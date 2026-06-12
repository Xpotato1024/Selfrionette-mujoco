# AGENTS.md

## 0. 参照順序

このリポジトリは `Selfrionette-mujoco` の source of truth として扱う。

参照順序:

1. `AGENTS.md`
2. `docs/architecture/development-policy.md`
3. `docs/architecture/mujoco-skeleton-first-spec.md`
4. `docs/conventions.md`
5. `docs/design/`
6. `docs/experiment-notes/`
7. `legacy/`

詳細な正本は `docs/README.md` の Source of Truth Map に従う。

## 1. 基本方針

MuJoCo 移行版は skeleton-first で進める。今回の architecture lock では
動く機能ではなく、責務境界と documentation SoT を固定する。

開発順序:

```text
Step 1:
  完全なスケルトンを作る

Step 2:
  各層に stub 実装を入れる

Step 3:
  stub 同士を runtime で結線する

Step 4:
  その後、各 stub の中身を 1 つずつ実装する
```

## 2. Source of Truth

- MuJoCo = physical source of truth
- Three.js = rendering only
- runtime = only composition root
- schemas = layer contract
- legacy = reference only
- assets = model assets

Three.js 側で FK / IK を再実装しない。MuJoCo、FK、Three.js hierarchy、
Rapier body、旧 PoseState がそれぞれ別々にアーム姿勢を持つ構造は禁止する。

## 3. 層と依存境界

標準層:

```text
input_sources
  → input_interpreters
  → motion
  → kinematics
  → mujoco_backend
  → transport
  → apps/mujoco-viewer
```

ただし複数層の結線は `runtime/` だけが行う。詳細は
`docs/architecture/dependency-boundaries.md` と
`docs/architecture/runtime-composition.md` を参照する。

## 4. Documentation SoT

`doc/` は使用しない。ドキュメントは `docs/` に統一する。
`docs/README.md` を SoT Map の正本とし、1 topic = 1 canonical document を守る。
詳細は `docs/architecture/documentation-sot-policy.md` を参照する。

## 5. Legacy / Assets / Rapier

- `legacy/` は参照元であり、新実装から直接 import しない。
- legacy script は top-level 副作用の可能性があるため、原則実行しない。
- `assets/` は採用する MJCF / XML / STL / mesh の置き場。
- Rapier world/body/collider/joint/physics step を新系統へ持ち込まない。
- 旧 PoseState は必要な場合のみ compatibility adapter とし、SoT にしない。

## 6. Hardware / Serial / OSC

明示的に scope 化されていない限り、serial port を開かない、OSC を送信しない、
実機を動かさない、hardware validation を実施しない。詳細は
`docs/operations/hardware-safety.md` を参照する。

## 7. Git 運用

`main` で直接作業しない。Codex が branch を作る場合は `codex/` 接頭辞を使う。

作業開始前:

```bash
git fetch origin
git switch main
git pull --ff-only
git status --short --branch
```

PR 作成前:

```bash
git branch --show-current
git diff --name-only origin/main...HEAD
git diff --check
git status --short --branch
```

PR 作成後:

```bash
gh pr view <pr> --json headRefName,baseRefName,headRefOid,changedFiles,mergeable,url
```

PR 更新報告前は local HEAD、PR head、remote branch HEAD の一致を確認する。
詳細は `docs/operations/git-pr-workflow.md` を参照する。

## 8. Validation

検証結果は category を分けて報告する。

- docs-only validation
- unit / compile validation
- MuJoCo model load validation
- Web typecheck / build
- dry-run
- hardware validation

dry-run、build、typecheck、MuJoCo model load を hardware validation と書かない。
詳細は `docs/operations/validation.md` を参照する。

## 9. Repository Naming / URL Guardrail

新規リンク、Issue URL、PR URL、docs path では `Selfrionette-mujoco` を使う。
旧名称や typo は historical note、legacy spelling、rename / migration 説明など、
意図がある場合だけ残す。

## 10. 最重要原則

動くものを早く作ることより、ズレない構造を先に作ることを優先する。

## 11. Architecture Boundary Tests

- import boundary は `docs/architecture/dependency-boundaries.md` と `tests/architecture/test_import_boundaries.py` を正とする。
- AGENTS.md の層図は data flow の説明であり、import dependency ではない。
- dependency boundary を変更する場合は、docs と test を同時に更新する。
- `tests/architecture` を削除・無効化してはならない。

## 12. PR / 作業報告の最低項目

PR本文と作業報告には、最低限以下を含める。

- Summary
- Changed Files
- Architecture Impact
- Validation
- Scope Exclusions
- Hardware Validation
- Serial / OSC / Hardware Access
- Remaining Risks

## 13. Scope Check

各作業報告では以下を明示する。

```md
legacy changed: 
legacy imported/executed:
assets changed:
schema breaking change:
import boundary changed:
MuJoCo package imported:
MuJoCo model load included:
MuJoCo forward included:
MuJoCo step included:
MuJoCoState snapshot included:
runtime composition included:
Three.js FK/IK included:
WebSocket included:
serial port opened:
OSC sent:
hardware validation included:
node_modules included:
dist included:
.env.local included:
docs / SoT impact checked:
```