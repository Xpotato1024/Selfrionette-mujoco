---
status: canonical
owner: contracts
last_verified: 2026-06-19
canonical_for:
  - runtime forward kinematics evaluation contract
related:
  - docs/contracts/forward-kinematics.md
  - docs/contracts/kinematics-command-contract.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/runtime-composition.md
  - src/selfrionette/runtime/evaluation.py
---

# Runtime Forward Kinematics Evaluation Contract

## 逶ｮ逧・
縺薙・譁・嶌縺ｯ縲｜ackend / runtime 蛛ｴ縺ｧ joint angles 縺九ｉ FK endpoint 繧定ｨ育ｮ励☆繧・蜀・Κ evaluation path 縺ｮ螂醍ｴ・ｒ蝗ｺ螳壹☆繧九Ｗiewer SoT 縺ｧ縺ｯ縺ｪ縺・・
P3 縺ｧ縺ｯ FK endpoint 繧定ｨ育ｮ励〒縺阪ｋ繧医≧縺ｫ縺吶ｋ縺縺代〒縲‥esired endpoint縲・MuJoCo site endpoint縲‘rror metric 縺ｮ邨ｱ蜷医・陦後ｏ縺ｪ縺・・
## 蜈･蜉・
- 蜈･蜉帙・ `JointCommand.joint_angles_rad` 縺ｾ縺溘・ qpos-like joint angles 縺ｧ縺ゅｋ縲・- P3 縺ｮ ordering 縺ｯ譌｢蟄倥・ `JointCommand` / qpos command boundary 縺ｫ蠕薙≧縲・- backend 縺ｧ padding 縺輔ｌ縺・qpos-like 蛟､繧剃ｽｿ縺・ｴ蜷医・縲《olver 蛛ｴ縺ｮ譛牙柑 joint
  count 繧呈・遉ｺ縺励※蜈磯ｭ縺九ｉ隧穂ｾ｡縺吶ｋ縲・- 遨ｺ縺ｮ joint angles 縺ｯ explicit failure 縺ｨ縺吶ｋ縲・- solver 縺ｮ譛溷ｾ・→髟ｷ縺輔′蜷医ｏ縺ｪ縺・・蜉帙・ explicit failure 縺ｨ縺吶ｋ縲・
## 蜃ｺ蜉・
- 蜃ｺ蜉帙・ FK endpoint 縺ｮ `Vector3` 縺ｧ縺ゅｋ縲・- unit 縺ｯ meter 縺ｧ縺ゅｋ縲・- coordinate frame 縺ｯ solver-defined frame 縺ｧ縺ゅｋ縲・- 縺薙・隧穂ｾ｡邨先棡縺ｯ `desired_endpoint_m` 縺ｨ閾ｪ蜍慕噪縺ｫ蜷御ｸ隕悶＠縺ｪ縺・・- 縺薙・隧穂ｾ｡邨先棡縺ｯ MuJoCo site endpoint 縺ｨ閾ｪ蜍慕噪縺ｫ蜷御ｸ隕悶＠縺ｪ縺・・
## Failure semantics

- 遨ｺ蜈･蜉帙・ `ValueError`縲・- 髟ｷ縺穂ｸ崎ｶｳ縺ｯ `ValueError`縲・- solver_joint_count 縺・0 莉･荳九↑繧・`ValueError`縲・- solver 縺悟・蜉幃聞繧呈拠蜷ｦ縺励◆蝣ｴ蜷医・縲√◎縺ｮ failure 繧偵◎縺ｮ縺ｾ縺ｾ陦ｨ髱｢蛹悶☆繧九・
## Viewer / transport boundary

- viewer 縺ｯ FK endpoint 繧貞・險育ｮ励＠縺ｪ縺・・- transport payload 縺ｫ evaluation field 縺ｯ霑ｽ蜉縺励↑縺・・- dry-run JSON 縺ｫ繧ゅ∪縺蜃ｺ縺輔↑縺・・
## Handoff

### P4 MuJoCo site endpoint extraction

P4 縺ｧ縺ｯ MuJoCo snapshot 縺九ｉ `tip` site endpoint 繧呈歓蜃ｺ縺吶ｋ縲１3 縺ｮ FK endpoint
縺ｯ site endpoint 縺ｧ縺ｯ縺ｪ縺・◆繧√￣4 縺ｧ縺ｯ MuJoCo world/site frame 縺ｨ縺ｮ豈碑ｼ・ｒ
譏守､ｺ縺励※謇ｱ縺・・
### P5 desired / qpos / FK / site / error metrics

P5 縺ｧ縺ｯ desired endpoint, qpos command, FK endpoint, site endpoint, error vector
繧剃ｸｦ縺ｹ縺ｦ豈碑ｼ・☆繧狗ｵｱ蜷・metrics helper 繧呈桶縺・・

- metrics は backend / runtime internal evaluation であり viewer SoT ではない
- desired_endpoint_m は command-side endpoint である
- qpos-like joint input は既存 `JointCommand` / qpos command boundary に従う
- FK endpoint は solver-defined frame である
- MuJoCo site endpoint は MuJoCo world / scene frame である
- frame が異なるため、error vector は diagnostic metric として扱い、physics truth / control correction には使わない
- `target_position_m` は viewer feedback / compatibility field であり、primary desired endpoint ではない
- output unit は meter で固定する
- missing desired / FK / site / qpos-like input は `ValueError` にする
- frame mismatch note は metrics object に保持し、P6 で dry-run / programmed input / WebSocket payload へ handoff する
- P7 で viewer read-only overlay へ handoff する
## Scope check

```text
viewer-side FK/IK: no
transport payload schema change: no
MuJoCo site extraction: no
desired/site/error metric integration: no
hardware validation: no
```
