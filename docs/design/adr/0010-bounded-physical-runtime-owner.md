---
status: historical
owner: runtime
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/contracts/physical-output.md
  - docs/contracts/pre-hardware-signal-emulation.md
---

# ADR 0010: 入力とphysical sessionを有限tickの単一ownerで接続する

## 背景と判断

#551は、別sessionのsignal previewではなく既存physical sessionへproduction入力を結ぶ。
現物の校正や#509 acceptanceを捏造せず、no-I/O testで結線を先行検証する。
既存planとdisarmed sessionを明示的に受け、arm/read/expiry/submit/closeを1つのownerが管理する。
session生成の大量の引数を別factoryへ複製しない。callable型のP5入力providerと受信callbackを必須にし、
missing physical evidenceをsimulation stateから生成した実測で代用しない。

## 時刻と失敗

装置timestamp、host monotonic、MuJoCo timeを区別する。元source commandは保持し、
physical-output requestはhost発行時刻を持つ別commandとして作る。qposは変更しない。
受信driverを入力より先にtickし、pending/cadence待ちでは入力を消費しない。
有限tick上限、stale、例外、拒否で停止し、全終了経路でreaderをcloseする。
callback実行後にも時刻と終了状態を確認し、古い入力やstop済みsessionへdispatchしない。
独自threadやhard real-time保証を設けず、callbackが返らない間の中断は保証しない。

## 却下した案

汎用scheduler/新しいtransport、暗黙clock変換、合成physical evidenceのproduction flag、
入力毎のauto-rearm、pending中のcommand queueは不要な責務/許可拡張のため採用しない。
既存SignalSessionをphysical sessionへ改名する案も、通過するgateを混同するため採用しない。

## 検証と残存境界

両source、P5 allow/non-allow、pending/timeout、stale/EOF/malformed、stop/abort/二重例外、
clockとidentityの不整合をfakeのみで試験する。既存permission・grant・evidence gateは緩めない。
実機用の受信callback、校正/配備identity/物理停止、長時間運用、動的servoは#516以降へ残る。
現在のcontractはphysical-output.mdへ同期し、本ADRを仕様の第二の正本にはしない。

## 監査後の補完判断

prepare中に375 msが経過すると、250 msの入力期限を超えても500 ms grant内で送信できる反例を確認した。
submit前のfreshness確認だけでは足りないため、既存sessionへprepare後のoptional拒否専用callbackを追加する。
True以外/例外で拒否し、Trueでも既存grant/generation/P5/permissionの最終照合を省略しない。
新しいsender wrapperやtimerは作らず、runtimeはこのcallbackを必ず渡す。in-flight sendの取消保証ではない。
