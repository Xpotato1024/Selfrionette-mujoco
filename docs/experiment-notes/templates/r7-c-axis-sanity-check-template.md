---
status: supporting
owner: operations
last_verified: 2026-07-30
canonical_for: []
related:
  - docs/operations/r7-c-axis-sanity-check.md
  - docs/operations/r7-c-live-loadcell-validation-log.md
---

# R7-C axis sanity check記録template

## 実行metadata

- Issue / PR:
- operator:
- 日付:
- local時刻:
- branch:
- commit:
- input source: keyboard / replay / live loadcell
- 関連#235 log:

## 安全確認

- Codex / CIによる実行: no
- Codex / CIによるserial port open: no
- Codex / CIによるCOM access: no
- OSC送信: no
- robot output: no
- actuator command: no
- firmware upload: no
- firmware変更: no
- physical axis確定: no
- force unit calibration確定: no

## 期待する観測

- input action:
- 期待するaxis direction:
- 期待するsign:
- 期待する`desired_endpoint_m`変化:
- 期待するpayload field:
- 期待するviewer表示:

## 実観測

- 観測したaxis direction:
- 観測したsign:
- 観測した`desired_endpoint_m` sample:
- 観測した`target_position_m` sample:
- 観測した`endpoint_evaluation` status:
- 観測frame数:
- operator confidence: high / medium / low

## 不一致の記録

- sign inversion疑い: yes / no / unknown
- axis mismatch疑い: yes / no / unknown
- 欠落metadata:
- malformed payload:
- live loadcellでpyserial利用不可:
- その他の異常:

## 判定

- pass / caution / fail:
- 理由:
- follow-up:
- #237へのhandoff:
