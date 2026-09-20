# Synthetic signal/contact fixtures

二つのJSONは同じRobot resource、home qpos、contact manifest、Task条件を使うsoftware-only fixture。
selfrionetteはchannel0をworld Xへ写像し、gamepadは既存viewer JSONを通す。wire順序/sign/offsetは
明示的な合成値であり実機calibrationではない。host/device clockは別fieldに残す。
半径0.01 mのsphereと0.001 mの初期gapは試験条件であり、実機形状や操作性能を表さない。
原実行手順とartifact contractはdocs/contracts/pre-hardware-signal-emulation.mdを参照する。
