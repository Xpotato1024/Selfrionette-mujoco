---
status: canonical
owner: architecture
last_verified: 2026-06-12
canonical_for:
  - hardware safety
related:
  - docs/operations/validation.md
---

# hardware safety

明示scopeがない限り、次の操作を行わない。

- serial portをopenする
- OSCを送信する
- hardwareを動かす
- 実hardwareを前提とするreceiver behaviorを変更する
- fixed-cycle modeを実装する
- hardware validationを実施する

将来のhardware-validation PRでは、実hardwareを使う前にpre-checklist、安全なdry-run手順、OSC compatibility
check、rollback手順、stop手順を追加しなければならない。
