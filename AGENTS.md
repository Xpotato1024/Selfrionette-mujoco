# AGENTS.md

## 0. 参照順序

このリポジトリは `Selfrionette-mujoco` の source of truth として扱う。

参照順序は以下とする。

1. `AGENTS.md`
2. `docs/architecture/development-policy.md`
3. `docs/architecture/mujoco-skeleton-first-spec.md`
4. `docs/conventions.md`
5. `docs/design/`
6. `docs/experiment-notes/`
7. `legacy/`

実装で迷った場合は、推測で進めず、上記の順に確認する。  
設計判断は `docs/design/` に残す。実験条件は `docs/experiment-notes/` に残す。  
既存資産の挙動確認や移植元の確認は `legacy/` を参照するが、`legacy/` を新実装の直接依存にしてはならない。

## 1. リポジトリの基本方針

このリポジトリは、Selfrionette の MuJoCo 移行版である。

目的は、旧 Selfrionette の段階的拡張で発生した責務混在を解消し、以下の層を明確に分離した上で再構築することである。

```text
input_sources
  → input_interpreters
  → motion
  → kinematics
  → mujoco_backend
  → transport
  → apps/mujoco-viewer
```

ただし、各層を直接数珠つなぎにするのではなく、結線は `runtime/` が行う。

```text
runtime = composition root
```

新規実装は、必ず既存スケルトンのどこかの層に収める。  
新しい責務が必要な場合は、先に設計文書を更新し、層の責務として定義してから実装する。

## 2. Skeleton-First 方針

このプロジェクトは skeleton-first で進める。

最初の目的は、シミュレータを動かすことではない。  
最初の目的は、責務境界が実装に侵食されることを防ぐことである。

開発順序は以下とする。

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

この順序を崩してはならない。

悪い進め方:

```text
入力を実装する
ついでに IK を書く
ついでに MuJoCo に渡す
ついでに表示も直す
```

良い進め方:

```text
入力層の箱を作る
運動生成層の箱を作る
MuJoCo 層の箱を作る
表示層の箱を作る
依存方向を固定する
stub を結線する
その後に中身を 1 つずつ実装する
```

## 3. Source of Truth

新系統では、MuJoCo を物理状態の Source of Truth とする。

正しい流れ:

```text
MotionCommand
  → MuJoCo model / data
  → body transform
  → site transform
  → MuJoCoState
  → Three.js 表示
```

禁止する流れ:

```text
MuJoCo
FK
Three.js hierarchy
Rapier body
旧 PoseState
がそれぞれ別々にアーム姿勢を持つ
```

Three.js 側でアーム FK を再計算してはならない。  
Three.js は MuJoCo から送られた transform を表示するだけにする。

## 4. 標準ディレクトリ構造

原則として、以下の構造を維持する。

```text
Selfrionette-mujoco/
  AGENTS.md
  pyproject.toml
  uv.lock

  assets/
    mujoco/
      fast_arm/
        arm.xml
        scene.xml
        meshes/

  legacy/
    fast_arm_control/

  docs/
    architecture/
      development-policy.md
      mujoco-skeleton-first-spec.md
      dependency-boundaries.md
      data-flow.md
    design/
    experiment-notes/
    operations/

  src/
    selfrionette/
      schemas/
      input_sources/
      input_interpreters/
      motion/
      kinematics/
      mujoco_backend/
      transport/
      runtime/

  apps/
    mujoco-viewer/

  tests/
    architecture/
    schemas/
    input_sources/
    input_interpreters/
    motion/
    kinematics/
    mujoco_backend/
    transport/
    runtime/

  scripts/
```

この構造を変更する場合は、PR 内で `Architecture Impact` を明記する。

## 5. 各層の責務

### 5.1 `schemas/`

共通データ構造を定義する層。

主な型:

```text
RawInputFrame
InputIntent
TargetCommand
JointCommand
MotionCommand
MuJoCoState
RenderState
```

ルール:

```text
- schemas はどの層にも依存しない
- 各層は schemas を参照してよい
- 層間の受け渡しは原則として schemas の型を使う
```

### 5.2 `input_sources/`

Arduino、keyboard、gamepad、replay、OSC、mocap などから入力値を取得する層。

許可:

```text
- デバイスから値を読む
- replay ログを読む
- RawInputFrame を返す
```

禁止:

```text
- IK
- target 更新
- joint angle 生成
- MuJoCo 操作
- WebSocket 送信
- Three.js 表示を意識した変換
```

### 5.3 `input_interpreters/`

`RawInputFrame` を `InputIntent` に変換する層。

許可:

```text
- deadzone
- scaling
- button / axis の意味づけ
- source ごとの入力解釈
```

禁止:

```text
- IK
- target 更新
- qpos / ctrl 生成
- MuJoCo 操作
- Three.js 表示用 transform 生成
```

### 5.4 `motion/`

入力意図から運動指令を生成する層。

許可:

```text
- target 位置更新
- workspace 制限
- 速度制限
- 安全制限
- IK 呼び出し
- JointCommand / TargetCommand / MotionCommand 生成
```

禁止:

```text
- MuJoCo model / data を直接操作する
- WebSocket 送信
- Three.js transform 生成
- 入力デバイスを直接読む
```

### 5.5 `kinematics/`

純粋な運動学を扱う層。

許可:

```text
- FK
- IK
- joint limit
- joint convention
- motor_space / joint_space 変換
```

禁止:

```text
- 入力デバイスを読む
- MuJoCo data.qpos / data.ctrl を直接操作する
- WebSocket 通信
- Three.js 表示
- runtime への依存
```

### 5.6 `mujoco_backend/`

MuJoCo を物理状態の SoT として扱う層。

許可:

```text
- MJCF / XML ロード
- model / data 管理
- qpos 反映
- ctrl 反映
- mj_forward
- mj_step
- body / site transform 取得
- contact 取得
- MuJoCoState 生成
```

禁止:

```text
- Arduino / keyboard / gamepad などの入力を直接読む
- InputInterpreter を直接呼ぶ
- runtime に依存する
- Three.js の描画処理を持つ
- WebSocket server を直接持つ
```

### 5.7 `transport/`

通信と記録を扱う層。

許可:

```text
- MuJoCoState の JSON 変換
- WebSocket 送信
- frame logging
- replay recording
```

禁止:

```text
- IK
- target 更新
- MuJoCo step
- 入力デバイス読み取り
- Three.js 表示
```

### 5.8 `runtime/`

全体を結線する composition root。

許可:

```text
- config 読み込み
- InputSource 選択
- InputInterpreter 選択
- MotionGenerator 選択
- MuJoCo backend 生成
- Transport 生成
- main loop 管理
```

ルール:

```text
- 複数層を結線してよいのは runtime のみ
- 各層は runtime に依存してはならない
```

### 5.9 `apps/mujoco-viewer/`

Three.js による表示層。

許可:

```text
- MuJoCoState を受け取る
- mesh / STL を表示する
- body / site transform を mesh に適用する
- target marker を表示する
- wrist / tip marker を表示する
- error vector を表示する
- joint ring を表示する
- debug overlay を表示する
```

禁止:

```text
- アーム FK を再計算する
- IK を実装する
- 入力から joint angle を生成する
- MuJoCo step を行う
- Rapier physics を新系統へ持ち込む
```

## 6. 依存方向

許可される依存方向:

```text
schemas
  ↑
input_sources
input_interpreters
kinematics
motion
mujoco_backend
transport
  ↑
runtime
```

許可例:

```text
input_sources       → schemas
input_interpreters  → schemas
motion              → schemas, kinematics
kinematics          → schemas
mujoco_backend      → schemas
transport           → schemas
runtime             → all layers
```

禁止依存:

```text
input_sources       → motion
input_sources       → kinematics
input_sources       → mujoco_backend
input_sources       → transport
input_sources       → runtime

input_interpreters  → motion
input_interpreters  → mujoco_backend
input_interpreters  → transport
input_interpreters  → runtime

kinematics          → input_sources
kinematics          → input_interpreters
kinematics          → mujoco_backend
kinematics          → transport
kinematics          → runtime

mujoco_backend      → input_sources
mujoco_backend      → input_interpreters
mujoco_backend      → motion
mujoco_backend      → transport
mujoco_backend      → runtime

transport           → input_sources
transport           → input_interpreters
transport           → motion
transport           → kinematics
transport           → mujoco_backend
transport           → runtime
```

依存境界を変更する場合は、先に `docs/architecture/dependency-boundaries.md` を更新する。

## 7. Legacy / Assets の扱い

### 7.1 `assets/`

採用するモデル資産を置く。

例:

```text
assets/mujoco/fast_arm/arm.xml
assets/mujoco/fast_arm/scene.xml
assets/mujoco/fast_arm/meshes/*.stl
```

モデル、STL、MJCF、XML、mesh の原点、座標系、単位を変更した場合は必ず文書化する。

### 7.2 `legacy/`

参照用の既存コードを保存する。

ルール:

```text
- legacy は移植元であり、新実装の依存先ではない
- legacy を直接 import しない
- legacy script は top-level 副作用を持つ可能性があるため、原則実行しない
- legacy の挙動を移植する場合は、責務単位で新しい層へ移す
- legacy を変更する場合は、理由と検証結果を docs/ に残す
```

## 8. Rapier / 旧 PoseState の扱い

MuJoCo 移行系統では、Rapier を物理エンジンとして使用しない。

禁止:

```text
- Rapier world
- Rapier rigid body
- Rapier collider
- Rapier joint
- Rapier physics step
```

旧 Selfrionette の `PoseState` は互換・比較・ログ参照のために扱ってよいが、新系統の中心に置いてはならない。

必要な場合のみ adapter を作る。

```text
MuJoCoState
  → PoseState compatibility adapter
```

ただし adapter は SoT ではない。

## 9. 作業環境

Python 環境は `uv` と `pyproject.toml` を正とする。

ルール:

```text
- 通常の実行は uv run python ... を使う
- 依存関係を追加・変更したら pyproject.toml と uv.lock を更新する
- pip install を手動実行して終わりにしない
- scripts/ には再現可能な起動手順を置く
```

Web frontend は `apps/mujoco-viewer/` 配下に置く。

ルール:

```text
- Vite + TypeScript + Three.js を基本構成とする
- node_modules/ をコミットしない
- dist/ をコミットしない
- frontend が FK / IK / MuJoCo step を持たないようにする
```

## 10. Git 運用

### 10.1 基本

```text
- main で直接作業しない
- 作業開始時に目的が分かる topic branch を作る
- Codex が branch を作る場合は codex/ 接頭辞を使う
- main へ直接 push しない
- force push しない
- unrelated file を巻き込まない
- .env.local や secret をコミットしない
- commit / push / PR / merge は別操作として扱う
- merge は明示指示があるまで行わない
```

### 10.2 Branch Hygiene / PR Diff Gate

作業開始前に以下を実行する。

```bash
git fetch origin
git switch main
git pull --ff-only
git status --short --branch
```

working tree が clean でなければ中止する。

topic branch 作成後に確認する。

```bash
git switch -c <expected-branch>
git branch --show-current
```

PR 作成前に確認する。

```bash
git branch --show-current
git diff --name-only origin/main...HEAD
```

PR 作成後に確認する。

```bash
gh pr view <pr> --json headRefName,baseRefName,headRefOid,changedFiles,mergeable,url
```

確認項目:

```text
- headRefName が expected branch である
- baseRefName が main である
- headRefOid が報告対象 commit である
- changedFiles が想定範囲内である
- unrelated file が含まれていない
```

branch を誤った場合は、その branch で修正を続けない。  
polluted PR は close し、最新 `main` から fresh branch を作り直す。

### 10.3 PR Update Verification Guardrail

「修正した」と報告する前に、local HEAD、PR head、remote branch HEAD の一致を確認する。

```bash
LOCAL_HEAD="$(git rev-parse HEAD)"
PR_HEAD="$(gh pr view <pr> --json headRefOid --jq .headRefOid)"
REMOTE_HEAD="$(git ls-remote origin <branch> | awk '{print $1}')"

echo "LOCAL_HEAD=$LOCAL_HEAD"
echo "PR_HEAD=$PR_HEAD"
echo "REMOTE_HEAD=$REMOTE_HEAD"

test "$LOCAL_HEAD" = "$PR_HEAD"
test "$LOCAL_HEAD" = "$REMOTE_HEAD"
```

PR head branch 上の実ファイル内容を remote から取得し、古い文言が消え、新しい文言が入っていることを確認する。

```bash
gh api \
  repos/Xpotato1024/Selfrionette-mujoco/contents/<path> \
  -f ref=<branch> \
  --jq '.content' | base64 -d > /tmp/<file>.remote

grep -n "<old text>" /tmp/<file>.remote || true
grep -n "<new text>" /tmp/<file>.remote || true
```

PR body だけを更新した場合も確認する。

```bash
gh pr view <pr> --json body,headRefName,baseRefName,headRefOid,changedFiles,mergeable,url
```

報告では local 確認と remote 確認を分けて書く。

## 11. GitHub Issue / PR Language Policy

GitHub Issue、Issue コメント、ロードマップ Issue、Phase Issue、PR 本文、PR コメント、作業報告は原則として日本語で作成する。

理由は、研究室メンバーや将来の共同開発者が、Issue 単体で作業意図・背景・完了条件を理解できるようにするためである。

例外として、以下は英語のままでよい。

```text
- ファイル名
- 関数名
- クラス名
- ブランチ名
- PR名
- コマンド
- 技術名
- GitHub label名
- 既存ドキュメント名
- 短い定義済みフレーズ
```

英語の設計文書や要件文書を Issue 化する場合は、英語本文を長く貼り付けず、日本語で要約・翻訳して記述する。

Issue 作成時に必要な GitHub label が存在しない場合は、必要な label を作成してから Issue に付与する。  
label 作成権限がない場合は、未付与 label と理由を報告する。

## 12. 編集ルール

```text
- テキストファイルは UTF-8 で保存する
- Shift_JIS / CP932 へ再保存しない
- 文字化けしたコメントや日本語は、意味を確認できる場合だけ直す
- 意味が確認できない場合は推測で翻訳しない
- 実験条件、単位、座標系、ポート番号、ログ形式を変更したら必ず文書化する
- 生成物をコミットしない
- secret や local env file をコミットしない
```

文字化け候補を見つけた場合は、代表的な mojibake パターンを検索し、修正範囲と未修正範囲を PR 本文に書く。

## 13. 標準検証コマンド

Python 側を含む変更では、原則として以下を実行する。

```bash
uv run pytest
uv run python -m compileall src tests
git diff --check
git status --short
```

`legacy/` を編集した場合のみ、必要に応じて以下を追加する。

```bash
uv run python -m compileall legacy
```

Web frontend を含む変更では、追加で以下を実行する。

```bash
cd apps/mujoco-viewer && npm install
cd apps/mujoco-viewer && npm run typecheck
cd apps/mujoco-viewer && npm run build
```

MuJoCo backend を含む変更では、可能な範囲で以下を確認する。

```text
- MJCF / XML load
- model names
- joint names
- site names
- qpos set
- mj_forward
- MuJoCoState snapshot
```

実機や通信を伴う変更は、dry-run、software validation、hardware validation を明確に分けて報告する。

## 14. Validation Category Distinction

検証結果は以下に分けて報告する。

```text
- docs-only validation
- unit / compile validation
- MuJoCo model load validation
- Web typecheck / build
- dry-run
- hardware validation
```

禁止表現:

```text
- dry-run 成功を hardware validation 成功と書く
- build 成功を hardware validation 成功と書く
- typecheck 成功を hardware validation 成功と書く
- MuJoCo model load 成功を実機成功と書く
```

hardware validation は、以下を含む可能性がある。

```text
- serial port open
- OSC send
- actual device connection
- firmware upload
- real robot motion
```

hardware validation を実施していない場合は `Not Run Reason` を書く。

## 15. Hardware / Serial / OSC Guardrails

実機、serial、OSC 送信は高リスク操作として扱う。

明示的に scope 化されていない限り、以下を行わない。

```text
- serial port を開く
- OSC を送信する
- 実機を動かす
- 実機前提の receiver 挙動を変更する
- fixed-cycle mode を実装する
- hardware validation を実施する
```

実機検証に進む前に、以下を文書化する。

```text
- 実機検証前チェックリスト
- 安全な dry-run 手順
- OSC 互換出力確認
- rollback 手順
- 停止手順
```

## 16. Scope Guardrails

各 PR は対象 Issue の scope に限定する。

禁止:

```text
- unrelated implementation を混ぜる
- unrelated docs cleanup を混ぜる
- 生成物をコミットする
- secret をコミットする
- legacy/ を明示 scope なしに変更する
- assets/ の座標系や単位を文書化なしに変更する
- schemas を互換方針なしに破壊的変更する
- apps/mujoco-viewer で FK / IK を実装する
- mujoco_backend に入力処理を混ぜる
- transport に motion / kinematics を混ぜる
```

## 17. Architecture Boundary Tests

責務境界はテストで守る。

`tests/architecture/test_import_boundaries.py` を置き、禁止依存を検出する。  
スケルトン作成後は、このテストを削除してはならない。

依存境界を変更する場合は、以下を同時に行う。

```text
- docs/architecture/dependency-boundaries.md を更新する
- import boundary test を更新する
- PR 本文に Architecture Impact を書く
```

## 18. Codex Prompt Compression Policy

今後の Codex 指示では、毎回すべての共通禁止事項、検証手順、報告形式を長文で繰り返さない。

個別プロンプトには、原則として以下だけを書く。

```text
- 対象 Issue または PR
- base branch
- working branch
- 目的
- 今回固有の作業内容
- 今回固有の禁止事項
- 今回固有の完了条件
- 今回固有の追加検証
```

共通ルールは、この `AGENTS.md` に従う。

ただし重要な PR や修正 PR では、以下を明記する。

```text
AGENTS.md の Branch Hygiene / PR Diff Gate に従う。
AGENTS.md の PR Update Verification Guardrail に従う。
AGENTS.md の Validation Category Distinction に従う。
```

## 19. 標準 PR 本文

PR 本文は原則として日本語で書く。

標準構成:

```markdown
## Summary

## Changed Files

## Design Decisions

## Architecture Impact

## Validation

## Scope Exclusions

## Hardware Validation

## Serial / OSC / Hardware Access

## Not Run Reason

## Linked Issue

## Remaining Risks
```

docs-only PR では、必要に応じて簡略化してよい。  
ただし、phase work、architecture boundary、schema、runtime、MuJoCo backend、transport、hardware guardrail に関わる場合は簡略化しない。

## 20. 標準作業報告

作業報告は原則として日本語で書く。

標準構成:

```markdown
## Summary

## Branch / Diff Gate

## Commit

## PR

## Changed Files

## Validation

## Scope Check

## Architecture Impact

## Documentation Impact

## Hardware Validation

## Serial / OSC / Hardware Access

## Remaining Risks
```

`Branch / Diff Gate` には以下の実測値を含める。

```text
- git branch --show-current
- git diff --name-only origin/main...HEAD
- gh pr view <pr> --json headRefName,baseRefName,headRefOid,changedFiles,mergeable,url
```

scope check では、対象 PR に応じて以下を明示する。

```text
- legacy changed
- legacy imported/executed
- assets changed
- schema breaking change
- import boundary changed
- MuJoCo XML changed
- MuJoCo model load included
- Three.js FK/IK included
- WebSocket included
- serial port opened
- OSC sent
- hardware validation included
- node_modules included
- dist included
- .env.local included
- docs / SoT impact checked
```

## 21. Repository Naming / URL Guardrail

新規リンク、Issue URL、PR URL、docs path では `Selfrionette-mujoco` を使う。

旧名称や typo は、historical note、legacy spelling、rename / migration 説明など、意図がある場合だけ残す。

新規追加箇所に旧リポジトリ URL を入れない。

確認例:

```bash
grep -R "Selfrionetto" -n docs AGENTS.md src tests apps || true
grep -R "Xpotato1024/Selfrionetto" -n docs AGENTS.md src tests apps || true
grep -R "Xpotato1024/Selfrionette/issues" -n docs AGENTS.md src tests apps || true
```

historical typo は機械的に全修正しない。  
ただし、新規設計文書では誤記を残さない。

## 22. 最重要原則

```text
動くものを早く作ることより、
ズレない構造を先に作ることを優先する。
```

```text
実装はスケルトンに従う。
スケルトンを実装に合わせて崩してはならない。
```

```text
Three.js は描画層。
MuJoCo は物理層。
Selfrionette core は入力・運動生成層。
runtime は結線層。
```

```text
legacy は参照元。
assets はモデル資産。
schemas は層間契約。
runtime は唯一の結線場所。
```
