# MuJoCo 4.0 記事用の再現・収録

MuJoCo 4.0.0 の柔軟体の弾塑性と投機的接触を、実際の物理計算から撮影するソフトウェア専用ツールです。
**通常の Xpotato-Sim / Web Viewer の4.0対応・実験環境の更新ではありません。** main の依存・lock、実機出力は変更しません。

## 実行

既存研究環境とは別の仮想環境を使います。Python 3.12、FFmpeg（libx264 / libvpx-vp9対応）、OpenGL描画環境が必要です。

```sh
python -m venv .venv-article
# Windows: .venv-article/Scripts/python.exe
.venv-article/bin/python -m pip install -r scripts/diagnostics/mujoco4_article/requirements.txt
.venv-article/bin/python -m pytest scripts/diagnostics/mujoco4_article/test_capture.py -q
.venv-article/bin/python scripts/diagnostics/mujoco4_article/capture.py --output /absolute/new/media-directory
.venv-article/bin/python scripts/diagnostics/mujoco4_article/contact.py --output /absolute/new/media-directory/contact
```

Linuxのheadless描画では `MUJOCO_GL=egl` とEGL/Mesaが必要です。Windowsでは通常のOpenGLを使用します。
出力先は新しいディレクトリに限定し、既存素材を上書きしません。外部通信、実機制御、公開操作はしません。
MuJoCo 4.0.0以外を明示的に拒否します。

## 比較条件

原本は Google DeepMind MuJoCo の `4.0.0`、commit `ac60eae30fa7e0d31315c38d9476752fb81be67e` の
`model/plastic/torsion.xml` と `foil.xml`。原本XMLとApache-2.0ライセンスを保持し、LF正本のSHA-256を検査します。
出力 `model.xml` は比較用の派生入力です。

- 3D棒：左右とも Young 120,000 Pa、Poisson 0.3、減衰0.025。右だけ `yield=0.025`。
- 2D薄板：左右とも Young 10,000,000 Pa、Poisson 0.3、減衰0.010、厚さ0.0048 m。右だけ伸び/曲げの `yield=0.00016 0.0016`。
- 両モデルとも3 ms刻み・discrete積分・CG。原本と異なる左右の減衰を統一し、foilのsolverをCGへ明示変更します。
- 材料の名前や色は実在材料の同定結果ではありません。荷重機構・球の初期条件をそろえていますが、変形中の接触力が同じという主張はしません。
- 接触例は4.0.0同士のflag OFF/ONです。半径10 mmの球が12 m/sで厚さ10 mmの壁へ向かう、20 ms刻みの意図的な粗い比較です。最初の1 stepの通過を比較し、全接触の非貫通を保証しません。

## 素材と証拠

`torsion/` と `foil/` にGIF、H.264 MP4、VP9 WebM、PNG/WebPの静止画を生成します。
800×500、20 fps、6秒、**0.3倍速**です。物理は3 msの固定刻みで進め、5 stepごとに撮影します。
最初のフレームはt=0、最後はt=1.785秒。6秒の表示時間はフレーム区間を含みます。
ループの終端では初期状態へ戻ります。動画の見た目を逆再生して弾性復元を作ることはありません。

元PNG120枚、フレーム時刻JSON、CSV、qpos/qvel/plasticのNPZ、原本/派生モデル/各フレーム/配布ファイルのhashを保存します。
最終測定は撮影後も計算を続けたt=4.8秒であり、GIFの終端時刻とは区別します。
全フレームで状態の有限性とMuJoCo警告を検査し、全圧縮ファイルをデコードします。
GIFは総表示時間も検査します。異なるOS・フォント・ドライバー・FFmpegによる画素や容量の差はあり得ます。

描画はMuJoCoの従来OpenGL rendererです。Filamentの性能・画質比較でも、通常のThree.js Viewerの録画でもありません。
`capture_wall_seconds_including_render_and_io` は描画と保存を含む所要時間で、制御系のRTFとして使わないでください。

## サイトへの引き渡し

素材はArticle Jobの非公開入力として扱い、siteのpublic/へ直接コピーしません。
GIF版は要求された比較用に保持します。軽量配信には同じ映像のMP4/WebMが有利ですが、サイト側の許可済みmedia契約・停止操作・静止画代替を確認してから採用します。
本ツールの成功は、公開承認、R2保存、媒体契約への適合、記事の独立監査の完了を意味しません。

関連：[LLM-01での観測](../../../docs/experiment-notes/mujoco4-article-20261111.md)。