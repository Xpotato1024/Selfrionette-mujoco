# canonical fast_arm MuJoCo asset

このdirectoryは、採用済み`fast_arm` MuJoCo assetのcanonical配置である。

## fileの責務

- `arm.xml`: canonical arm model定義。
- `scene.xml`: `arm.xml`をincludeするcanonical scene wrapper。
- `meshes/`: arm model用canonical STL mesh directory。
- `viewer-profile.json`: Robot Pluginが所有するversioned viewer declarationのserializable SoT。

## path contract

- `arm.xml`は`meshdir="meshes"`を使用し、`meshes/`からmeshを解決する。
- `scene.xml`は同じdirectoryの`arm.xml`をincludeする。
- STL filenameは既存の`Sholder`という綴りを含むlegacy asset名を維持する。
- backend model、viewer model URL、VFS mappingの対応は`ROBOT_PLUGIN`のresource declarationと
  `viewer-profile.json`で明示し、robot IDから推測しない。

## 変更規則

- mesh scale、axis、origin、unitを変更する場合は、先に関連canonical docsを更新する。
- joint、body、site、actuator、default pose、geom shape、inertial parameter、joint range、control rangeは
  model contract dataであり、asset onboardingだけを目的とする変更では編集しない。
- assetの由来は`legacy/fast_arm_control`だが、新実装からlegacy Python codeをimportまたは実行しない。
