# Arduino firmware

current candidateとlegacy referenceを分離する。このindexはboard、port、parameterの正本ではない。

- `loadcell_7ch_pro_micro/`: current 7-channel sender candidate
- [legacy_selfrionette](legacy_selfrionette/README.md): provenanceを保持したreference
- [serial frame contract](../../docs/contracts/r7-a-lite-serial-frame-contract.md)
- [hardware safety](../../docs/operations/hardware-safety.md)

upload、serial open、実機validationはsoftware-only testと別のside effectである。
