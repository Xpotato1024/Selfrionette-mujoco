---
status: supporting
owner: research
last_verified: 2026-11-11
canonical_for: []
---

# MuJoCo 4.0 記事素材の観測

2026-11-11、LLM-01（Windows / i7-9700K / RTX 2070 SUPER）、Python3.12.13の隔離環境で実行した。
Sim基点は `d3e667b461ff0d795c03afb9bbe43fc7c68201da`。通常環境のMuJoCo3.9.0とlockは変更していない。
手順・固定入力は[収録ツール](../../scripts/diagnostics/mujoco4_article/README.md)を参照する。

## 実行と観測

`capture.py` の2シーンと `contact.py` を実行した。元モデルは4.0.0の固定upstream commit、比較条件はツールのREADMEに記録した。
下記は材料特性を実験同定した結果ではなく、設定されたモデルの数値計算である。

| t=4.8秒の観測 | 弾性側 | 弾塑性側 |
|---|---:|---:|
| 3D棒の上端回転角 | -0.000237° | 81.973151° |
| 3D棒の全flex頂点の初期位置からのRMS変位 | 0.460 mm | 28.541 mm |
| 2D薄板の全flex頂点の初期位置からのRMS変位 | 0.489 mm | 19.172 mm |

各モデルの全状態が有限で、MuJoCo警告は0。回転角は上端capのhinge角、RMSは全flex頂点の変位であり、材料ひずみそのものではない。
6秒GIFは1.8秒未満の物理時間を0.3倍速で示す。上記の最終値とは測定時刻が異なる。

接触比較ではt=0の球中心x=-120 mm、vx=12 m/s。20 ms後、OFFではx=+120 mm、ONではx=-17.1 mmだった。
ONの接触候補は実接触前から作られる。これは同じ4.0.0のflag差であり、3.xとの比較や、実アームの貫通問題の解決を示すものではない。

## 配布容量（LLM-01 / FFmpeg 8.1.2）

同じ800×500・120フレームのPNG列から生成した。GIF128色、H.264 CRF23、VP9 CRF32なので、厳密な同品質比較ではない。

| 素材 | GIF | MP4 | WebM |
|---|---:|---:|---:|
| 3Dねじり | 703,339 bytes | 76,723 bytes | 56,449 bytes |
| 2D薄板 | 729,077 bytes | 88,232 bytes | 71,847 bytes |

両形式を実デコードし、GIFは120フレーム・計6000 msを確認した。Linux CI再生成ではフォント・描画・エンコーダが異なるため、容量とhashを別記録にする。
実素材と詳細manifestは非公開作業ディレクトリに保存し、Gitへ大きな映像・PNG列は追加しない。

## 互換性検査の範囲

既存 `tests/mujoco_backend` はMuJoCo4.0.0の隔離環境で51件成功。異常入力を意図的に与える2件からNumPy RuntimeWarningが出るが、検査自体は成功した。
既存native診断でcanonical fast_armモデルのload/forwardと4自由度を確認した。
これは通常Viewer/WASM、制御写像、全runtime、保存trial、実操作RTFの4.0互換性を保証しない。

独立監査、被験者評価、実機動作、serial、OSC、deployは実施していない。