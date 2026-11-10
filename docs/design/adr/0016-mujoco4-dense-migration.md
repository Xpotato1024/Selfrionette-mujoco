---
status: supporting
owner: architecture
last_verified: 2026-11-11
canonical_for: []
related:
  - docs/operations/validation.md
  - docs/contracts/mujoco-state.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
  - docs/experiment-notes/2026-11-11-mujoco4-migration.md
---

# ADR 0016: 投機的接触を使わないMuJoCo 4.0.0への移行

## 決定と適用範囲

MuJoCo nativeと公式WASMをともに4.0.0へ固定し、既存の小規模な剛体・関節ばねタスクを移行する。
本記録は移行実装の判断であり、mainへのマージ、実機安全、参加者実験の受入を承認した記録ではない。
物理状態は引き続きPython nativeが所有し、WASMは描画だけを行う。
投機的接触は無効、現行タスクの1/600秒・implicitfast・Newton・50反復・tolerance 1e-10を維持する。
既存の物体、Robot質量・慣性・関節・actuator、初期姿勢、入力写像、接触係数を変更しない。

## 背景と根拠

3.9.0と4.0.0を同じ簡易衝突モデルで比較した予備測定では、投機的接触OFFの4.0.0が速かった。
10 physics stepsの処理時間中央値を3反復間で中央値にすると、非接触0.051006→0.038739 ms、
接触保持0.0722085→0.0580475 msだった。元archiveの26 fileのSHA-256と、比較6試行の生データからの
中央値を再検証した。条件とarchive identityは[移行検証記録](../../experiment-notes/2026-11-11-mujoco4-migration.md)に置く。
これはAMD EPYC上のnative-only合成試験であり、製品アプリ全体のRTF向上、統計的有意差、
全場面の高速化を証明しない。3.9.0からの累積変更であり、4.0.0単独の変更に改善を帰属させない。

腕本体の貫通はcollider不足という別問題である。版更新だけで非貫通が成立したとは扱わない。
collider追加、投機的接触、新積分法、柔軟体、Robotなしのscene、起動時版選択は独立した変更とする。

## 既知不具合を避ける範囲

[upstream issue #3767](https://github.com/google-deepmind/mujoco/issues/3767)は、4.0.0の疎行列Choleskyで
誤った因子分解が起こり、疎な制約ヤコビアンを使うNewtonが誤った加速度・遅い収束・発散を生じ得る問題である。
小さなRobotでも疎行列を明示すれば対象になるため、腕の自由度だけで判定しない。

`mujoco_backend.compatibility.validate_solver_compatibility`は、実効engineが4.0.0で、
`mj_isSparse(model)`が真かつsolverがNewtonの場合に、loader/providerのreset・最初のforwardより前に拒否する。
密行列・別solverへの自動変更は行わない。構成が大きくなった場合に黙って不具合経路へ入らないための制約である。
59/60/61自由度および明示dense/sparseのnativeモデルで境界を検査する。4.0.0のautoは実測で60以上が疎行列だった。
将来版を模したunit testは版判定の分岐検査だけであり、未リリース版の動作保証ではない。

現在のresearch-spring、dynamic-fixed-contact、dynamic-cube-drop、dynamic-cube-pushは、
最終モデルのnvが5・8・14・14で、3.9.0/4.0.0ともに密行列Newton、投機的接触OFFだった。
この4条件について上記不具合経路を避けられると判断する。任意の将来sceneまで保証しない。

## 互換性修正

`mj_fullM`の新API `(model, data, destination)`に質量行列の鏡映検証を移行する。数値の検証内容は維持する。
初期姿勢診断では、対称候補の評価値の1e-16程度の差によって選択が逆転することを確認した。
順位計算に限って小数12桁へ丸め、同点ならqpos辞書順昇順、最後にcandidate ID降順で決める。
実測値とhard constraintは丸めず、固定済みhome姿勢・モデルを変更しない。
これは対称解の再現可能な選択規則であり、負の肘角が物理的に優れているという主張ではない。

## 検証・採用と戻し方

Python既存回帰、追加guard、モデル読み込み・物理応答・reset・記録、WASM実API/表示・typecheck/buildを検証する。
ソフト入力の比較結果と実操作RTFの受入は区別し、未実施の参加者・実機検証を完了扱いにしない。
数値の差が許容範囲を超える、既知不具合経路が必要になる、実操作で性能が悪化する場合は本採用しない。

比較元は`d3e667b461ff0d795c03afb9bbe43fc7c68201da`のsourceと両lockで保持する。
戻す際は移行変更をまとめてrevertし、`just setup`で両依存と固定Web buildを同期する。
Pythonだけ・WASMだけを手動で戻さない。試行の既存`mujoco_version`、model/condition digest、source revisionを保持し、
3.9.0と4.0.0の試行を同じ実験条件として混ぜない。

## 代替案

3.9.0維持は変更リスクが最小だが、観測済みの改善候補を試せない。
修正版4.0.xを待つ選択もあるが、現行密行列タスクについては対象外を実測でき、起動拒否も設けられる。
したがって4.0.0の限定移行を進め、修正版の採用はその版の回帰検証で別途判断する。
