---
status: canonical
owner: architecture
last_verified: 2026-06-12
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
- このadoption stepで許可するのはpath修正だけであり、model semanticsの変更は禁止する。
- Step 4-Bではheadless model loaderのcanonical load pathとして
  `assets/mujoco/fast_arm/scene.xml`を使用する。
- MuJoCoのimportは`src/selfrionette/mujoco_backend/`内に限定する。
- loaderとinspection helperは、まだruntimeへ接続しない。
- `MuJoCoState` snapshot生成は#10へ送る。

他の文書ではasset ruleを再記載せず、この文書へlinkする。
