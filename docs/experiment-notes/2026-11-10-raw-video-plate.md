---
status: supporting
owner: runtime
last_verified: 2026-11-10
canonical_for: []
related:
  - docs/operations/offline-video-export.md
  - docs/contracts/object-scene-contact-diagnostic.md
---

# 可動板ばねとraw動画のソフトウェア確認

## 条件

旧立方体の物理条件を上書きせず、`tasks/research-spring-plate`を追加した。
可動板は100×10×100 mm、質量0.1 kgの仮定、接触面Y=-0.31 m、剛性100 N/m、
減衰2 N s/m、world -Y方向、範囲0–50 mmである。実物から同定した値ではない。

Gamepad入力契約へプログラム生成列を供給し、合成clockで780 tick / 13秒を記録した。
0–1秒中立、1–4秒+0.35、4–7秒中立、7–10秒-0.35、10–13秒中立。
実Gamepad、Selfrionette、被験者を用いていない。正式programmed_target plugin経路とも区別する。

## 観測

最大変位0.0175924370268 m、最大接触点力1.8038444868 N。
今回の入力では押し込み・保持・解放・復帰を確認し、native安全停止は発生しなかった。
Taskのsuccessは13秒の観測期間満了であり、押圧再現成績を意味しない。
旧立方体での同じ入力と比較して、保持した並進質量・接触面・ばね定数に対応する挙動を確認した。
形状・慣性・model digestが異なるため、一般に同じ実験条件とは主張しない。

別に`tasks/dynamic-cube-drop`の双腕sceneを180 tick / 3秒記録した。
停止理由はsimulation_budgetであり、成功判定へ書き換えない。ばね専用fieldがない記録も
同じ動画用bundleへ渡せることを確認した。

## 検証経路

既存strict readerで元trialを検査し、保存qposを公式MuJoCoへ適用したsite位置との差は0 m。
物理stepを禁止した回帰でも旧ばね・可動板ばね・落下のbundle生成が成功する。
初回raw映像は1920×1080、30 fps、390 frame / 13秒で生成し、全frameのデコードを確認した。
タイトル、字幕、計器、分割画面はなく、canvasは1つ。browser例外0、animation loopなし。
表示用座金を薄い物理板へ重ねない回帰も追加した。

再生成commandは[raw動画出力](../operations/offline-video-export.md)に記載する。
MP4、試行ログ、個別入力生成scriptはrepository外に保持する。
動画出力速度は実操作RTFではなく、ログI/O負荷・実入力遅延・実機受入は別途の検証対象である。
