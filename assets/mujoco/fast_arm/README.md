# fast_arm logical resource path

このdirectoryにはproduction resourceを置かない。`assets/mujoco/fast_arm/...`はviewer、payload、
VFS、diagnosticsが維持するstable logical identifierであり、physical repository pathではない。

## fileの責務

- `fast_arm_core:resources/model/arm.xml`: canonical arm model定義。
- `fast_arm_core:resources/model/meshes/`: arm model用canonical STL mesh directory。
- Selfrionette adapter `resources/mujoco/scene.xml`: canonical scene wrapper。
- Selfrionette adapter `resources/viewer-profile.json`: versioned viewer declaration。
- Selfrionette adapter `resources/fixtures/`: viewer debug fixture。

## path contract

- `arm.xml`は`meshdir="meshes"`を使用し、`meshes/`からmeshを解決する。
- `scene.xml`は同じdirectoryの`arm.xml`をincludeする。
- STL filenameは既存の`Sholder`という綴りを含むlegacy asset名を維持する。
- backend model、viewer declaration / model / fixture / VFSのlogical pathとpublic URLの対応は
  `ROBOT_PLUGIN`のresource declarationと`viewer-profile.json`で明示し、実行時にrobot IDから推測しない。
- package resourceはtyped owner/path declarationから解決し、旧directoryへのfallbackやchecked-in duplicateを持たない。

## 変更規則

- mesh scale、axis、origin、unitを変更する場合は、先に関連canonical docsを更新する。
- joint、body、site、actuator、default pose、geom shape、inertial parameter、joint range、control rangeは
  model contract dataであり、asset onboardingだけを目的とする変更では編集しない。
- assetの由来は`legacy/fast_arm_control`だが、新実装からlegacy Python codeをimportまたは実行しない。
