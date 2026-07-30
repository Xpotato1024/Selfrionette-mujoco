# scripts

repository operationを補助する明示実行scriptの入口である。script名の一覧を正本化せず、用途別directoryと
canonical operationへrouteする。

## responsibility

- `repository/`: Markdown / GitHub body等のrepository validation
- `viewer/`: viewer fixture exportとbrowser / live smoke
- `diagnostics/`: software-only Robot diagnostics
- `hardware/`: serial / deviceを扱いうるoperator-gated script

## safety

`hardware/`のscriptは閲覧だけで実行せず、
[hardware safety](../docs/operations/hardware-safety.md)に従ってdevice、port、stop手順を確認する。
diagnosticsやdry-runをhardware validationと呼ばない。

## canonical routing

- [validation](../docs/operations/validation.md)
- [backend / viewer startup](../docs/operations/backend-viewer-startup.md)
- [hardware safety](../docs/operations/hardware-safety.md)
