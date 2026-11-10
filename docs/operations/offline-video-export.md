---
status: canonical
owner: operations
last_verified: 2026-11-10
canonical_for:
  - validated finite-trial raw video export
related:
  - docs/contracts/finite-trial-runtime.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
---

# 保存ログから装飾なしの動画を出力する

論文・発表用の素材は、通常Viewerの3D sceneを単一視点で出力する。
タイトル、字幕、計器、phase表示、分割画面、軸、接触力矢印を焼き込まない。
床、Robotの材質・配色、物体、ばねの表示は通常Viewerと共通である。
注釈や字幕が必要な場合は、元動画とは別に編集する。

## 入力と準備

`terminal.json`まで確定した有限試行directoryを指定する。元のtrialは変更しない。
`trial-continuous/v1`の参照連鎖・hashを検証し、保存条件から再構築したmodelのdigestを照合する。
対応するsource revision、既存のPython環境、Viewerの`npm ci`済み依存、Node、FFmpeg/FFprobe、
Chrome/Edge/Chromiumが必要。新たなbrowserを自動downloadせず、既存installか`--browser`を使う。
実デバイス、シリアル接続、実行中Workbenchは不要である。

```powershell
uv run python scripts/viewer/export_trial_video.py results/TRIAL_ID videos/run.mp4
# 視点・解像度・fpsを明示する場合
uv run python scripts/viewer/export_trial_video.py results/TRIAL_ID videos/side.mp4 --camera side --width 1280 --height 720 --fps 30
```

既定は1920×1080、30 fps、operator視点。cameraはoperator/iso/front/side/topから選ぶ。
必要なら`--browser`へbrowser実行fileの絶対pathを渡す。専用の一時profileを作り、
ユーザーの既存browserやログインsessionには接続しない。配信先はloopbackだけである。

## 時刻と描画

simulation時刻に基づく等速再生で、各動画frameにはその時刻以前の最新の記録姿勢を採用する。
補間した未記録姿勢を生成せず、logより高いfpsでは同じ姿勢を繰り返す。
出力長は元の記録期間を1動画frame未満で切り上げる。タイトルや終端の余分な静止時間は加えない。

原理は保存qposの再描画であり、入力の再実行や物理積分`mj_step`ではない。
Python側の公式MuJoCoで保存site位置との整合性を検査し、通常ViewerのWASM表示経路で姿勢を投影する。
描画は明示したframeごとに行い、wall-clock animation、リアルタイム録画、WebSocket入力は使わない。

物理実行→ログ確定→動画生成を分けるため、動画の描画・符号化負荷を実行中の制御loopへ加えない。
ログI/Oは別に負荷が残り、動画生成速度を実操作RTFや入力遅延と解釈しない。

## 出力と失敗

MP4と同名JSONへ、元trial・source revision・model/terminal hash・fps・出力frame数・camera・
再構成誤差・browser例外・動画SHA-256を保存する。説明情報は映像に焼き込まず、このsidecarへ分離する。
出力前にFFprobeでcodec/寸法/fps/frame数を照合し、FFmpegで全frameをデコードする。
既存のMP4/JSONは上書きせず、試行内への出力も拒否する。失敗時は診断用export logを残す。

不完全記録、破損hash、異なるmodel、欠測姿勢、未記録mocapのあるmodel、描画/符号化エラーは
動画生成成功へ置換しない。描画中のbrowser/serverは終了時に回収する。
有限試行formatが対応範囲であり、任意CSVや入力だけのReplayを自動推測するconverterではない。

## タスク共通性と研究上の境界

ばねのIDや変位、特定Robotの関節数を動画出力条件に含めない。
単腕のばね可動板と双腕のキューブ落下で同じcommandを確認する。
失敗・中断trialも記録として有効なら出力できるが、停止理由はsidecarへ残る。
映像を作れたことは研究課題の達成、実機受入、被験者実験の結果を意味しない。
旧Viewerと新Viewerの条件・revisionを混在させない。
