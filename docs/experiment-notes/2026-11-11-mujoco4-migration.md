---
status: supporting
owner: research
last_verified: 2026-11-11
canonical_for: []
related:
  - docs/design/adr/0016-mujoco4-dense-migration.md
  - docs/operations/validation.md
---

# 2026-11-11 MuJoCo 4.0.0移行のソフト検証

## 比較条件と主張範囲

比較元は`d3e667b461ff0d795c03afb9bbe43fc7c68201da`の3.9.0、候補は同sourceからの4.0.0移行である。
LLM-01の別worktree・別project環境を使用し、Python 3.12.13、NumPy 2.4.6を揃えた。
source/lock以外の既存作業tree・実機・入力デバイスへ書き込んでいない。
現行taskの物理条件とmodel XMLは変更せず、双方でnvと`mj_isSparse`を実測した。

| Task | nv | 実効Jacobian | Solver | 投機的接触 |
|---|---:|---|---|---|
| research-spring | 5 | dense | Newton | OFF |
| dynamic-fixed-contact | 8 | dense | Newton | OFF |
| dynamic-cube-drop | 14 | dense | Newton | OFF |
| dynamic-cube-push | 14 | dense | Newton | OFF |

4.0.0の既知不具合へのgateは実効設定で判断する。autoの59/60/61自由度を実行すると59はdense、
60/61はsparseだった。説明文の「60以下dense」ではなく`mj_isSparse`を正とする。

## 先行native計測の再利用

元archiveは`mujoco_collision_audit_2026-11-11.zip`、SHA-256は
`f9ac71ebb4852b5f79cad691f22b5c5b9bdf15b56d513cf987f3cfef0d3b172b`。
manifest掲載26 fileのhashとsizeを再照合し、比較6試行の各600 batchの生時間からp50を再計算した。
元archiveは別保存であり、ここには抽出結果と元file hashを置く。

[検証済み抽出結果](2026-11-11-mujoco4-migration-data/prior-native.json)は、AMD EPYC 9V74 / Linux、
Python 3.12.14 / NumPy 2.3.5での5自由度・簡易collider付き合成fixtureのnative-only結果である。
両版とも投機的接触OFF。同じscene/物理parameterで、10 physics steps（1/60秒のsimulation時間）あたりの処理時間。

| 条件 | 3.9.0のp50、3反復中央値 | 4.0.0のp50、3反復中央値 |
|---|---:|---:|
| 非接触 | 0.051006 ms | 0.038739 ms |
| 接触保持 | 0.0722085 ms | 0.0580475 ms |

モデル・物理parameterの一致は元evidenceで確認されているが、製品colliderではない。
この数値をLLM-01実操作のRTF改善率へ換算しない。全場面の優越や統計的有意差は未検証。

## 互換性の切り分け

3.9.0の全集合は4,218 passed / 13 skipped。skipは既存のOS条件等で、移行のために追加していない。
4.0.0初回のfocused検証は4 failed / 271 passedだった。失敗を削除・skipせず次の通り対処した。

- 新しいguard testのauto=60の期待値を、59/60/61のnative実測に合わせて訂正した。
- 既存の質量行列鏡映testを`mj_fullM(model, data, destination)`へ移行した。数値assertは維持。
- 初期姿勢診断の対称候補の順位が1e-16程度の差で逆転した2 testを、順位だけの丸めと明示同点規則で修正した。
  home姿勢と既存assertは変更していない。raw評価とhard constraintの閾値も維持。

修正箇所を含む39 testは通過。最終の4.0.0全集合は**4,239 passed / 13 skipped**。
JUnitのtest IDを照合し、既存4,231件の欠落なし、追加21件、skip対象同一を確認した。
候補名の大小を逆転した同点testをさらに強化し、neutral_initial_poseの11件も再実行して通過。
Viewerの既存test/typecheck/production build、mypy（既存scopeとlauncher）、Ruff、compileも通過した。
通常のuv同期による同じproject環境の3.9.0→4.0.0更新も確認し、core/studioの実効版とモデル構築を検証した。
[検証台帳](2026-11-11-mujoco4-migration-data/validation.json)に件数、追加ID、raw JUnit hash、source hashを保持する。
これらはsoftware validationであり、実Gamepad/Selfrionette、参加者実験や実機安全の検証ではない。

## 再現入口

各比較checkoutで、その版の`uv.lock`とViewer lockを使用する。versionだけを手動差替えした環境を使わない。

```powershell
uv sync --locked --group dev --python 3.12 --no-python-downloads
uv run pytest tests -q
uv run mypy
uv run mypy scripts/workbench_local.py
uv run ruff check src tests scripts .github
cd apps/mujoco-viewer
npm ci
npm test
npm run typecheck
npm run build
```

既存のprovider処理の比較入口は`measure_simulation_hot_path.py`を使う。出力先はrepository外の既存directoryへ置く。

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
uv run python scripts/diagnostics/fast_arm/measure_simulation_hot_path.py --output ../hot-path.json --ticks 120 --no-profile --plain
```

このdiagnosticは同じ100 tickの入力で片側/両側接触へ移行し、その後の保持を測る合成sceneであり、
実際の操作者入力・通信・保存・描画を含むend-to-end RTFとは異なる。

## 残る受入

実操作経路のRTF/遅延は別途受け入れる。コリジョン追加・投機的接触・4系の柔軟体拡張は本検証の対象外。
この移行をもって腕本体の貫通が修正済み、または全sceneの動作が保証されたとしない。

## LLM-01でのprovider処理比較

両全集合テストの終了後、同じi7-9700K / Windows端末で既存diagnosticを3反復ずつ実行した。
順序は3.9→4.0、4.0→3.9、3.9→4.0。各scenario 120 tick、接触条件は100 tickの接近後、
計測中の入力速度は0 m/s。既存の手先球と幅広い固定cubeを使い、腕本体colliderは追加していない。
以下はproviderのsnapshot・prepare/commit・sample・serializationを含む1 control tickの処理時間で、
各反復p50/p95の3反復間中央値。入力・WebSocket・永久保存・GUI描画は含まない。
OSや他アプリの負荷を固定したbenchmarkではないため、有意な高速化やworst-case期限保証を主張しない。

| 条件 | 3.9.0 p50 | 4.0.0 p50 | 3.9.0 p95 | 4.0.0 p95 |
|---|---:|---:|---:|---:|
| 非接触 | 1.10510 ms | 1.02585 ms | 1.2366 ms | 1.1443 ms |
| 片手接触保持 | 1.34125 ms | 1.30470 ms | 1.4649 ms | 1.4104 ms |
| 両手接触保持 | 1.51045 ms | 1.51000 ms | 1.6656 ms | 1.5960 ms |

今回の中央値では非接触と片手接触が短縮、両手接触はほぼ同等である。native-onlyの先行計測の改善率を、
このprovider処理や実操作RTFへ一般化しない。[比較結果](2026-11-11-mujoco4-migration-data/hotpath.json)に
各反復のp50/p95/max、元reportのSHA-256、source hashと数値差を残す。

model SHA-256、scene、native物理parameter、optionは一致した。第1反復の同一tickの比較では、
最大qpos差6.2723e-10、最大qvel差1.3079e-8だった（このsceneはhinge関節のみなのでrad / rad/s）。
接触geom pairごとに力を集約して比較し、左右の力が相殺されて差が隠れないようにした。
これは有限の合成入力系列の比較であり、あらゆる入力での数値同値性や長時間挙動を証明しない。
