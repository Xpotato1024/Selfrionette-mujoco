---
status: canonical
owner: architecture
last_verified: 2026-07-17
canonical_for:
  - model asset contract
related:
  - assets/mujoco/fast_arm/README.md
---

# asset契約

この文書は、MJCF、XML、STL、scale、axis、origin、mesh配置の前提に関する
canonical contractである。

## Robot Plugin resource ownership

新しいrobotの標準配置は`assets/mujoco/<robot_id>/`と`configs/<robot_id>/`である。ただし、
generic catalog、runtime、viewerはrobot IDからpathを組み立てない。`ROBOT_PLUGIN`の
`RobotResourceDeclaration`がmodel、configuration、viewer VFS resourceのrepository-relative pathを
明示し、`ViewerRobotDeclaration`がmodel URL、model resource path、VFS path / resource / URL対応を
明示する。

production discoveryはcatalog registryを公開する前に、全resourceが許可されたrepository root内の
実fileへ解決すること、Profileのmodel / configuration referenceと一致すること、viewer declarationと
backend resource declarationが一致することを検証する。MJCFの`include`とmesh / texture / hfield fileは
宣言済みVFS mappingで解決できなければならない。absolute path、`..`によるescape、remote URL、missing
resourceはstartup failureであり、warning skipまたはrobot ID由来pathへのfallbackを行わない。

## fast_armのcanonical asset

- canonical pathは`assets/mujoco/fast_arm/`である。
- 必須fileは次のとおり。
  - `arm.xml`
  - `scene.xml`
  - `meshes/BaseLink.stl`
  - `meshes/SholderLink1.stl`
  - `meshes/SholderLink2.stl`
  - `meshes/UpperArmLink.stl`
  - `meshes/ForeArmLink.stl`
  - `viewer-profile.json`
- `arm.xml`はcanonicalなmesh directory contractである`meshdir="meshes"`を使用し、
  `assets/mujoco/fast_arm/meshes/`からmesh fileを解決しなければならない。
- `scene.xml`は同じdirectoryの`arm.xml`をincludeしなければならない。
- STL filenameは、既存の`Sholder`という綴りを含め、legacy asset名を維持する。
- joint、body、siteの名前はmodel contractの一部であり、stable identifierとして扱う。
- asset path修正とmodel semantics変更を同じ変更として暗黙に扱わない。
- headless model loaderのcanonical load pathは`assets/mujoco/fast_arm/scene.xml`である。
- MuJoCoのimportは`src/selfrionette/mujoco_backend/`内に限定する。
- state snapshotのownershipはbackend / runtime contractに従う。

他の文書ではasset ruleを再記載せず、この文書へlinkする。
