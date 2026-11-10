# ソフトウェア比較用の4条件

このフォルダの条件 JSON は Workbench の JSON import で読む。共通タスク
`tasks/research-spring` の同じ robot、`single_original` model、ばね scene、
`contact_observation_task` を使用する。入力sourceと画面力表示のON/OFFを切り替えるための例であり、
Gの速度係数は0.1 m/s、Sは0.02 m/sのため、この4fileをそのまま同一速度の比較条件とは扱わない。

| 条件 | 入力 | 表示 |
| --- | --- | --- |
| `gamepad-no-force-cue.json` | Gamepad | OFF |
| `gamepad-force-cue.json` | Gamepad | ON |
| `selfrionette-fixture-no-force-cue.json` | 合成 Selfrionette fixture | OFF |
| `selfrionette-fixture-force-cue.json` | 合成 Selfrionette fixture | ON |

Selfrionette の identity・校正・mapping は software fixture の例示値であり、
実機の識別値や校正値ではない。実機では正規 profile と接続設定を別途取得・入力し、
role・neutral の検証を通す。フォルダ名は実験データの取得を意味しない。
Workbench でデモを選んだ場合、実験記録は作られない。実験の閾値や知覚結果は定義しない。

条件と順序の準備には`xpotato-sim experiment prepare`を使う。
このフォルダの`gamepad-no-force-cue.json`と`selfrionette-fixture-no-force-cue.json`を入力し、
`--speed-m-s`で共通係数を、`--software-fixture`で合成入力の確認用途を明示する。
共通モデル・scene・Task・有限予算・表示縮尺等を照合し、G/S × ON/OFFの4条件を新しいdirectoryへ出力する。
重みや校正値は推測・修正しない。実操作者用sessionでは、実物から確認したSelfrionette条件へ置き換える。

追加の力覚提示デバイス開発は凍結中で、画面力表示の比較は継続する。
Taskの観測時間満了は押圧成功を意味せず、ばね復元荷重`kq`は接触力や指先入力力とは別量である。
正式課題の選択、主指標・閾値、反復・待機・練習・休止規則は、この例では決定しない。
prepare → Workbenchの実験モードで記録 → attach → analyzeのコマンドと制約は
[自己pilotの実行手順](../../../docs/operations/experiment-pilot.md)を参照。

[有限試行](../../../docs/contracts/finite-trial-runtime.md)、
[Workbench](../../../docs/contracts/workbench.md)、
[profile 配置と移行](../../../docs/operations/profile-roles-and-migration.md)を参照。


現在の4条件例は`tasks/research-spring-plate`を使用する。可動端は100×10×100 mmの板であり、
旧`tasks/research-spring`の立方体とは異なるscene/model条件である。旧保存結果を上書きしない。
記録から装飾なしの動画を出す手順は[raw動画出力](../../../docs/operations/offline-video-export.md)を参照する。
