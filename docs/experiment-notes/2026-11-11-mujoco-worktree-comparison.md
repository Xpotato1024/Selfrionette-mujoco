---
status: supporting
owner: research
last_verified: 2026-11-11
canonical_for: []
related:
  - docs/design/scene-only-and-mujoco-version-selection.md
  - docs/operations/validation.md
  - docs/contracts/finite-trial-runtime.md
---

# 移行前後の独立worktree比較

## 固定対象

本人の追加方針に基づき、2026-11-11にWindowsの同一端末で作成・検証した。
mainはPR #644で4.0.0へ移行済み。旧版へのrevert、同じsourceでの版切替、旧比較treeへのbackportは行わない。

| 用途 | source commit | native | WASM |
|---|---|---|---|
| 移行前 | `d3e667b461ff0d795c03afb9bbe43fc7c68201da` | 3.9.0 | 3.9.0 |
| 更新後main（選定時） | `2a65e30ea0ca8557eee3241591e4ab3953f34459` | 4.0.0 | 4.0.0 |

両worktreeはdetached HEAD、prune防止lock付き。`.venv`、WASMのnode_modules、build出力、uv/npm cacheを別々に用意した。
Python依存はcopy方式で導入し、worktree間で実行依存を共有しない。Python 3.12.13、NumPy 2.4.6、
Node 24.22.1、npm 11.19.1を揃えた。各commitの `uv.lock` / `package-lock.json` を使い、導入・測定前後のhashを照合した。

`uv sync --locked --group dev --python 3.12.13 --no-python-downloads --link-mode copy` と `npm ci` を使い、
版だけを手動インストールする操作は行っていない。nativeの `mj_versionString` とロード済みWASMの同APIでも版を照合した。

## 検証結果

- 両側でPython依存整合検査、Viewer全test、型検査、production buildが成功。
- 追加のbackend検査は3.9.0で51件、4.0.0で68件成功。skipなし。
- 計測入口の取り違え拒否11件成功。commit、dirty tree、native/WASM、Python patch、core構成、別venv/source/WASMの混入を検査した。
- 全計測で実行前後のcommit、lock、import先、実版とbinary hashが一致。両worktreeは終了時もclean。
- research-spring / fixed-contact / cube-drop / cube-pushのnvは5/8/14/14で、両版とも密行列Newton、投機的接触OFFだった。

backendの初回検査では一時directoryの親がなく1件が環境エラーになった。親directoryを作成して対象検査を再実行し、
成功結果を別に記録した。テストの削除・skip・assert緩和はしていない。異常値を意図的に入力する2件の既存NumPy警告は残る。

## 測定と来歴

既存 `measure_simulation_hot_path.py` を変更せず、worktreeごとのPythonで呼び出した。
別のphysics loop、記事専用実行経路、CI workflowは追加していない。外側の記録用ツールはローカルの比較workspaceに置いた。
各runは120 tick × 3 scenario、3反復ずつ。順序は3.9→4.0、4.0→3.9、3.9→4.0。

各runの前後にsource commit、native/Python/WASM版、依存・モデル・条件・scriptのhashを保存し、
元測定JSONのSHA-256と実行command、開始/終了時刻を紐づけた。公開用の集約記録にはローカル絶対pathを含めない。

全conditionのhashは版の違いにより異なる。差分を再帰照合すると `condition.mujoco_version` だけだった。
このfieldだけを明示除外した数値条件、Scene、model、使用diagnostic sourceは一致する。
元conditionの不一致を隠したり、異なるengineの試行を同一条件として混ぜたりしない。

| scenario | 3.9.0 p50（3反復中央値、ms） | 4.0.0 p50（3反復中央値、ms） |
|---|---:|---:|
| 非接触 | 1.10825 | 1.06215 |
| 片手接触保持 | 1.43265 | 1.31660 |
| 両手接触保持 | 1.56410 | 1.48355 |

同じ端末・同じ診断の移行前後比較であり、source commitにはAPI適応やguardなどの差分もある。
OS/他アプリの負荷を固定しておらず、統計的有意差・MuJoCoだけの因果効果・全sceneの優越を主張しない。
GUI、通信、永久保存、実デバイスを含むend-to-end RTFではない。

[集約記録（版・commit・lock・各run hash）](2026-11-11-mujoco-worktree-comparison.json)から元証拠に追跡する。
raw archive `sim-worktree-comparison-20261111.zip` は比較workspaceに保全し、
SHA-256 `8db677589ae034874c7c0b9c609452e9d2d905efac6c6ec69a09e32f2cd5a52a`、1,028,530 bytes。
測定・比較用ファイルだけを含み、venv/node_modulesやcacheを同梱しない。

## 継続方針

旧版はこのcommitの比較専用。柔軟体・球体・Robotなし等は更新後mainからの汎用機能として実装する。
新しいmainと比較する際は新しい固定worktreeと測定記録を作り、今回のworktreeをpullして変更しない。
PR #643の旧記事専用実行は依然として未採用。今回の環境分離完了を、その汎用化や実操作・実機受入の完了としない。

Hardware / serial / OSC / merge / deploymentは未実施。mainと既存研究用checkoutは変更していない。
