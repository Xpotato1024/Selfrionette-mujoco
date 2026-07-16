---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - model asset contract
related:
  - assets/mujoco/fast_arm/README.md
---

# asset契約

この文書は、MJCF、XML、STL、scale、axis、origin、mesh配置の前提に関する
canonical contractである。

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
