---
status: canonical
owner: operations
last_verified: 2026-06-27
canonical_for:
  - R7-E-P1 fast_arm endpoint motion sanity
related:
  - docs/README.md
  - docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md
  - docs/contracts/target-marker-desired-endpoint.md
  - docs/contracts/mujoco-model-name-contract.md
  - docs/architecture/runtime-composition.md
---

# R7-E-P1 fast_arm endpoint motion sanity

## 目的

この文書は、R7-E の cube task に進む前提として、`fast_arm` が初期姿勢から
`x / y / z` 方向の small endpoint command に対して、期待方向へ動くかどうかを
確認・記録・説明する gate を固定する。

ここで固定したいのは、`cube` scene や contact metric ではない。
先に `tip` site の方向性 sanity を見て、backend / runtime / viewer の
責務境界を崩さずに次へ進めるかを判断する。

## この gate で見るもの

- fast_arm initial pose
- current tip site position
- desired endpoint
- target command
- resulting `qpos[0:4]`
- resulting tip site position
- commanded delta direction
- actual tip movement direction
- `desired_endpoint_m` と `target_position_m` の混同
- viewer feedback と backend source-of-truth の逆転有無

## 実行方法

human check の再現用に、次の CLI を用意した。

```powershell
uv run python scripts/run_fast_arm_endpoint_motion_sanity.py
```

任意で `--base-desired-endpoint-m` と `--command-delta-m` を変更できる。
ただし、検証の基準は「小さい command を与えたときに、`tip` site の変化を
軸ごとに説明できること」であって、任意 3D 到達の完成ではない。

## 判定の見方

各 axis について、result は structured に返る。

- `pass`: command の軸と tip 変化の軸・符号が一致している
- `rejected`: solver / runtime が command を明示的に拒否した
- `limitation`: command は通ったが、現 solver の制約や frame mismatch のために
  期待方向へは見えない
- `unavailable`: backend exception などで result を作れなかった

result は少なくとも次の観点を持つ。

- `desired_endpoint_m`
- `target_position_m`
- `qpos_before`
- `qpos_after`
- `initial_tip_position_m`
- `final_tip_position_m`
- `actual_delta_m`
- `direction_dot`
- `reason`

## x / y / z の観点

- `+x` / `-x`: 期待方向に move するかを確認する
- `+y` / `-y`: 現 solver で limitation になってもよい
- `+z` / `-z`: 期待方向に move するかを確認する

`y` 方向が未対応、あるいは不自然に見える場合は failure ではなく、
現 solver / fast_arm IK v0 の limitation として記録する。
backend crash や unexplained jump は許容しない。

## cube task に進める条件

- x / z の small command について、result を説明できる
- y の limitation がある場合、その理由を status / reason で説明できる
- `desired_endpoint_m` と `target_position_m` の役割を取り違えていない
- viewer は read-only のままで、backend の結果を壊していない

## 中間発表で言えること

- fast_arm の初期姿勢から endpoint command を与え、MuJoCo 上の `tip` site の変化を
  軸方向ごとに確認する sanity procedure を追加した
- `pass / rejected / limitation` を明示的に残すようにした
- `desired_endpoint_m` と `target_position_m` の境界を説明できるようにした

## 中間発表で言いすぎてはいけないこと

- 完全な 3D IK が完成した
- 任意の 3D target に自然に到達できる
- 実機 fast_arm の軸整合が完了した
- cube を物理的に押せることを確認した

## 参考実装

- runtime helper: `src/selfrionette/runtime/endpoint_motion_sanity.py`
- CLI script: `scripts/run_fast_arm_endpoint_motion_sanity.py`
- 既存 procedure: `docs/operations/r7-d-p3-fast-arm-endpoint-command-check-procedure.md`
