---
status: canonical
owner: architecture
last_verified: 2026-07-16
canonical_for:
  - parallel work boundaries
related:
  - docs/architecture/dependency-boundaries.md
  - docs/architecture/runtime-composition.md
  - docs/reports/audits/canonical-content-history-separation-2026-07-16.md
---

# 並列作業契約

## 正規flow

```text
input source -> interpreter -> motion / kinematics -> MuJoCo backend
             -> measured MuJoCoState -> transport -> rendering-only viewer
```

parallel workはこのflowとownerを分裂させない。schema変更、composition変更、viewer表示、evidence作成は
別touch areaとして扱い、同じfileまたは同じGitHub bodyへ並列writeしない。

## Boundary規則

- schemasはcontract shapeだけを所有し、runtime behaviorを持たない。
- input layerはphysical stateまたはqposを直接更新しない。
- motion / kinematicsはcommandとpredictionを返し、MuJoCo stateを直接変更しない。
- backendはvalidated commandを適用し、post-step physical stateを測定する。
- transportはserialize / deliveryだけを行う。
- viewerはrendering-onlyで、FK / IK / physicsを再実装しない。
- multi-layer wiringは`runtime/`だけが所有する。
- public contractを変える作業は、consumer、canonical doc、focused testを同じ変更で整合させる。

## Integration gate

並行sliceを統合する前に、base、actual diff、overlap、contract version、focused validationを確認する。
未対応shape、unknown profile、unavailable measurementを暗黙fallbackで吸収しない。hardware / serial /
deploymentは専用taskとoperator gateがない限りscope外とする。

pre-auditのintegration chronologyは
`docs/reports/audits/canonical-content-history-separation-2026-07-16.md`へ保存した。
