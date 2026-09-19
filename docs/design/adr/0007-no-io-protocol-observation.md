---
status: historical
owner: runtime
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/contracts/physical-output.md
  - docs/contracts/pre-hardware-signal-emulation.md
---

# ADR 0007: 実機許可と信号previewを分離し、応答判定だけを共有する

## 背景

#542は実機なしでwireと応答処理を検証する。既存FastArmPhysicalOutputSessionは
#509のaccepted physical measurementを要求するため、偽evidenceを生成して利用しない。

## 決定

pure joint変換、generic OSC codec、router parser/correlationを再利用する。
実機用sessionからACK判定だけを小さな共通moduleへ移し、permission/safety/send lifecycleは保持する。
previewはno-I/O専用で、実機用sendable wrapperやgrantを生成しない。
peerはwire bytesだけを読み、期待commandを渡して成功を作らない。
有限driverはcallerのnonblocking receiveとclockを受け、tickごとの件数とtimeoutを検査する。
新しいscheduler、thread、network listener、自動reconnectは作らない。
現行契約はphysical-outputとpre-hardware-signal-emulationを正本とする。

## 代案と判断

- 偽#509 evidenceでphysical sessionを通す: simulationとphysical authorityを混同するため採用しない。
- preview専用parser/correlationの再実装: productionと乖離するため採用しない。
- 汎用通信frameworkを新設する: 今回必要な機能を超えるため採用しない。
- 実UDP loopbackでpeerを作る: byte境界の検証はin-memoryで可能なため採用しない。

## 受入と制約

golden bytes、同一判定の両session、timeout/identity/stopと負の対照を検証する。
callback自体のblockingを中断する仕組みではなく、OS/driver時間保証は与えない。
疑似応答はphysical ACK、運動、停止の証拠にはならない。#543と実機gateは別に残る。
