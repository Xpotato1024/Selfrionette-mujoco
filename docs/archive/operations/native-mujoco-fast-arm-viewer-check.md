---
status: draft
owner: operations
canonical_for:
  - native MuJoCo fast_arm viewer check
related:
  - docs/operations/backend-viewer-startup.md
  - docs/operations/browser-visual-smoke.md
  - assets/mujoco/fast_arm/README.md
---

# Native MuJoCo fast_arm Viewer Check

## 目的

`fast_arm` の初期姿勢と mesh の見え方を、browser viewer の修正に入る前に MuJoCo native 側で確認した。

## 実行コマンド

```powershell
uv run python scripts/view_fast_arm_native_mujoco.py --no-viewer
uv run python scripts/view_fast_arm_native_mujoco.py --key-name home --no-viewer
uv run python scripts/view_fast_arm_native_mujoco.py --key-name home
```

補助確認として native renderer でも 2 枚の画像を出した。

- `qpos0`
- `home` keyframe

## model path

- `assets/mujoco/fast_arm/scene.xml`
- `scene.xml` は `arm.xml` を include する
- `arm.xml` は `meshes/` を `meshdir="meshes"` で参照する

## qpos / keyframe 概要

- `nq=4`
- default `qpos0 = [0.0, -1.5707963267948966, 0.0, 0.0]`
- keyframe は 1 個
- keyframe 名は `home`
- `home` のcurrent `qpos = [0.0, -0.5235987755982989, 0.0, -1.0471975511965976]`

## native viewer / native renderer の観察結果

- `qpos0` では arm は横方向に伸びた姿勢で表示された
- `home` keyframe はP22でlower / bent neutral poseへ更新された
- body / joint / site の接続は破綻していない
- mesh の asset path は全て解決でき、STL も 5 本ともロード対象として揃っている

## body / geom の確認メモ

- body frame は `base_link -> sholder_link_1 -> sholder_link_2 -> upper_arm_link -> fore_arm_link` の順で連結されている
- MuJoCo の geom には mesh local の `pos` / `quat` が入っている
- browser viewer は現在、body transform を直接 STL に載せる実装で、geom local pose は使っていない

## browser viewer との差分

native 側では mesh の local pose が model に含まれているが、browser 側は `fastArmMeshes.ts` で body pose のみを使っている。

そのため、browser 側で mesh が body frame に素直に追従して見えても、native viewer の mesh 見え方とは一致しない可能性が高い。

## PR #174 の判断

- `#174` は native viewer 確認待ちのまま merge しない
- いまの差分は model / asset の破綻よりも browser viewer の mesh transform 再現不足として扱うのが妥当
- 追加の browser viewer 修正は、native viewer の mesh local pose を前提にした follow-up で扱う

## classification

- B: native viewer は成立しているが browser viewer の coordinate mapping / mesh transform 側が不足

## remaining risks

- browser 側に MuJoCo model loading を入れずに、どう mesh local pose を再現するかは follow-up が必要
- runtime / product viewerのinitial pose policyはP22で`home` keyframeに統一された
