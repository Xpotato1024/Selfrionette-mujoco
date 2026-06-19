# MuJoCo WebViewer OSS / WASM viewer 調査メモ

調査日: 2026-06-19

## 背景

`#175` と `PR #176` により、`assets/mujoco/fast_arm/scene.xml` は MuJoCo native viewer 上で自然な下垂姿勢で表示され、`home` keyframe も `qpos = [0, 0, 0, 0]` であることを確認した。

一方で `PR #174` の browser Three.js viewer は、fast_arm mesh の姿勢・接続・初期姿勢の再現がまだ不自然だった。

このため、browser 表示 fidelity の改善候補として、公式 `@mujoco/mujoco` を isolated PoC で確認した。

## Native viewer 確認結果の要約

- model path: `assets/mujoco/fast_arm/scene.xml`
- `qpos0`: `[0.0, -1.5707963267948966, 0.0, 0.0]`
- keyframe `home`: `[0.0, 0.0, 0.0, 0.0]`
- native viewer では `home` が自然な下垂姿勢
- body / joint / site の接続は破綻していない

## 候補一覧

- `@mujoco/mujoco`
- `mjswan`
- `zalo/mujoco_wasm`

今回の PoC では、公式 package を第一候補として先に検証した。`mjswan` と `zalo/mujoco_wasm` は fallback 候補として残し、今回は実装していない。

## PoC 実行方法

PoC は production viewer とは切り離して、`experiments/mujoco-wasm-viewer-poc/` に作成した。

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco\experiments\mujoco-wasm-viewer-poc
npm ci
npm run dev -- --host 127.0.0.1 --port 4173
```

ブラウザ URL:

```text
http://127.0.0.1:4173/experiments/mujoco-wasm-viewer-poc/
```

## `@mujoco/mujoco` PoC 結果

- candidate: `@mujoco/mujoco`
- location: `experiments/mujoco-wasm-viewer-poc/`
- model: `assets/mujoco/fast_arm/scene.xml`
- keyframe lookup: `model.key("home")`
- asset loading: `scene.xml`, `arm.xml`, 5 個の STL mesh を VFS に投入して成功
- visual result: browser 上で model/data はロードでき、`home` qpos も適用できた
- build result: `npm run typecheck` / `npm run build` は成功
- result classification: `PoC-only`

### 実際に確認できた値

- `nq = 4`
- `nv = 4`
- `nbody = 8`
- `ngeom = 7`
- `nmesh = 5`
- `nkey = 1`
- `default qpos = [0, -1.5707963267948966, 0, 0]`
- `home qpos = [0, 0, 0, 0]`

### 補足

WASM 初期化は `locateFile` を明示しないと失敗したため、PoC では `@mujoco/mujoco/mujoco.wasm?url` を使って Vite 配信 URL を明示した。

### Matrix4 変換メモ

初期実装では `geom.mat` / `geom.pos` から配列を作り、`mesh.matrix.fromArray(...)` に渡していた。しかし `fromArray` は配列要素をそのまま内部 `elements` にコピーするため、MuJoCo 側の row-major 配列をそのまま渡す用途には向いていない。

現在は `Matrix4.set(...)` で組み立てた `Matrix4` を `mesh.matrix.copy(...)` に渡している。

`fromArray` をやめた理由:

- `fromArray` は MuJoCo の row-major 意図を反映しない
- `Matrix4.set(...)` は row-major の意図を保ったまま Three.js に渡せる
- `mesh.matrix.copy(...)` により、local matrix を明示的に差し替えられる

### Primitive axis

primitive geom の axis は現時点では既存変換を維持している。

- cylinder / cone 系は `CylinderGeometry` を使い、`rotateX(Math.PI / 2)` で軸を合わせている
- matrix 修正後、さらに camera framing と lighting を足したことで、fast_arm の link 構造は読める状態になった
- それでも native viewer との完全な parity には至っていないため、残りは表示調整の差分として扱う

## current Three.js viewer との比較

- current viewer は payload / rendering の責務分離は維持できているが、fast_arm の mesh attachment と姿勢再現がまだ不自然
- official WASM PoC により、browser 上で MuJoCo model / data を直接扱うこと自体は可能と確認できた
- ただし、PoC の時点では current viewer の置換先として十分ではない
- browser renderer 側の camera / lighting / mesh 表示品質まで含めた別設計が必要

## 採用判断

- adopt / PoC-only / reject: `PoC-only`
- rationale:
  - model load と `home` keyframe 適用はできた
  - ただし native viewer と同等の見え方をそのまま保証する段階ではない
  - production viewer 置換の判断材料にはなるが、直接統合はまだ早い

## `#174` handling recommendation

- `#174` はこの PoC をもって自動的に merge しない
- browser viewer の mesh transform / frame 解釈は `Matrix4.set(...)` ベースに修正した
- PoC 側でも camera framing と lighting を足して link 構造を読める状態にしたが、native viewer と完全一致ではない
- 次の一手は、`@mujoco/mujoco` を production に混ぜることではなく、browser 表示系の設計方針を別 issue で整理すること

## 次 issue 候補

1. current browser viewer の mesh transform / joint frame / camera framing を native viewer と比較して再点検する issue
2. `@mujoco/mujoco` PoC 側で camera framing / lighting / material をさらに詰める issue

## Remaining risks

- `@mujoco/mujoco` の Windows support は README 上でも experimental 扱い
- WASM 配信は `locateFile` 依存で、dev/build 経路の差分に注意が必要
- browser 側で MuJoCo scene を直接描画しても、native viewer と同じ camera / lighting / mesh fidelity が自動で得られるわけではない
- current viewer の不自然さが、mesh transform 由来か camera / lighting 由来かはまだ分離が必要
## 2026-06-19 update

`#185` で option B 相当の WASM scene viewer が product viewer に昇格した。`apps/mujoco-viewer` は `@mujoco/mujoco` を production dependency として使い、browser WASM は `qpos` を受けて描画するだけに限定している。
`#186` の follow-up で旧 Three.js 手実装 viewer は削除し、product viewer の code path を wasm-scene に一本化した。
