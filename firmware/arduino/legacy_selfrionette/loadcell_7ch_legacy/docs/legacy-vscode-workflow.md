# Legacy VSCode / PlatformIO Workflow Notes

このメモは、元の Arduino / PlatformIO 資産に VSCode ベースの作業フローが存在した可能性を残すための参照ノートである。

- `.vscode/` は raw copy していない。
- 理由は、`c_cpp_properties.json` や `launch.json` にローカル絶対パスと個人環境依存の設定が含まれていたためである。
- こうした設定は repository の参照資産としては不安定なので、repo には入れない。
- 実際の IDE 再現はこの PR の scope 外であり、`#164` で整理する対象は手順と観測点に限る。
- 書き込み経路、monitor 経路、環境依存の port 指定は `#164` で整理する。
- ここでは、VSCode + PlatformIO の workflow があったことだけを記録する。

## 方針

- ローカル PC 固有のパスは repo に入れない。
- `.vscode/` の中身は、必要な論点だけを手書きで残す。
- 生成物や build cache は reference asset に含めない。
- IDE 設定の再現を必要とする場合は、実行可能な手順ではなく、後続 issue で再設計する。
