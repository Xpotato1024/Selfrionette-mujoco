# firmware

hardware firmwareとlegacy referenceの入口である。Python runtime、schema、viewerの
source of truthではない。

- [Arduino firmware](arduino/README.md)
- [serial frame contract](../docs/contracts/r7-a-lite-serial-frame-contract.md)
- [hardware safety](../docs/operations/hardware-safety.md)

README閲覧やcompileはhardware accessではない。serial open、upload、実機作動は
canonical operationのoperator gateなしに実行しない。
