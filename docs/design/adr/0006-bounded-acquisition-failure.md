---
status: historical
owner: architecture
last_verified: 2026-09-20
canonical_for: []
related:
  - docs/contracts/r7-a-lite-serial-frame-contract.md
  - docs/contracts/pre-hardware-signal-emulation.md
---

# ADR 0006: 有限取得の失敗は偽sampleを作らずsessionへ返す

## 状態と背景

R7-L-P2 / #541の実装判断。readerの無限line探索とliveの空read反復を廃止する。
今回の目的はsoftware-onlyで取得失敗を再現・停止できること。実機の時間保証ではない。

## 決定

既存read_frameの成功型とwire grammarを維持し、取得不能は例外で伝播する。
有限timeout、line/byte budget、bounded診断保持をsourceに置く。runtimeは既存finallyでcloseする。
失敗したsessionは明示close/startまで再使用せず、自動再送・自動再接続をしない。
経過時間だけのstaleは新しい成功vectorで回復できるが、read失敗によるラッチとは区別する。
未受信とzero vectorを区別し、host receipt clockとdevice timestampも分離する。
既定のinjected clockは再現性のため静的とし、時間試験には明示fake clockを注入する。
数値・例外・状態遷移の正本はserial frame contractで一元管理する。

## 代案と理由

None/no-data resultを返すpoll APIは、runtime全入口・scheduler・ログの契約拡張を要するため今回は採用しない。
最後のsampleやzeroで埋める方法は、取得失敗を正常な操作と混同するため採用しない。
background reader thread、自動再接続、未知のstartup待ち時間推定も追加しない。

## 制約と検証

startup/calibration中の長い無信号でも有限に失敗する。実機で必要な待ち方はoperator手順と実測から後で決める。
OS/driver停止やcaller提供のblocking callbackまでhard real-timeに中断できるとは主張しない。
fake serial/clockで境界を検証し、production Mapping/MuJoCoでも取得失敗後の追加指令・stepがないことを確認する。
#542の通信peerや#543の統合runner、physical validationはこの判断だけでは完了しない。
