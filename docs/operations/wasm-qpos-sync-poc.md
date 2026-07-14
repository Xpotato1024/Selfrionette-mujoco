---
status: historical
owner: operations
canonical_for:
  - historical wasm qpos sync PoC evidence
related:
  - docs/design/mujoco-wasm-scene-renderer-design.md
  - docs/research/mujoco-webviewer-options.md
  - docs/operations/product-viewer-wasm-scene-renderer.md
---

# WASM qpos sync PoC

> Status: historical. The executable PoC was promoted to `apps/mujoco-viewer`
> by #185 and retired by #385. The current fixture owner and operator procedure
> are documented in `docs/operations/product-viewer-wasm-scene-renderer.md`.

## 目的

この PoC は、Python native MuJoCo backend 由来の `qpos` を browser 側の MuJoCo WASM scene viewer に同期できるかを確認する。

重要な boundary は次のとおり。

- Python native MuJoCo backend が source of truth
- browser WASM MuJoCo は visual renderer candidate only
- browser 側で `qpos` を再計算しない
- browser 側で IK / FK を移植しない

## fixture schema

PoC は次の JSON 形式を読む。

```json
{
  "schema_version": 1,
  "source": "python-native-mujoco",
  "model_path": "assets/mujoco/fast_arm/scene.xml",
  "preset": "sweep_x",
  "qpos_length": 4,
  "frames": [
    {
      "frame_index": 0,
      "t_s": 0.0,
      "qpos": [0.0, 0.0, 0.0, 0.0],
      "metadata": {
        "phase": "initial_hold"
      }
    }
  ]
}
```

検証条件:

- `schema_version` は `1`
- `qpos_length` は `model.nq` と一致する
- `frames` は空でない
- 各 frame の `qpos` は number array である

## fixture generation command

```powershell
uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30
```

生成された fixture は `apps/mujoco-viewer/public/fixtures/fast_arm_sweep_x_qpos.json` に置く。下記のplayback記述はPoC時点のhistorical evidenceであり、削除されたPoCを現行手順として実行しない。

## playback smoke

PoC UI では次の操作を確認する。

- Load fixture
- Play
- Pause
- Step next
- Step previous
- Reset to home

smoke 上の関係は次のとおり。

- initial load では `home` keyframe を適用する
- fixture load 後は selected frame の `qpos` を `data.qpos` に適用する
- play は fixture sequence を進める
- reset は `home` keyframe に戻す

## WebSocket live qpos

この PoC では live WebSocket qpos reader は実装していない。

理由:

- 必須要件は fixture-based qpos sync である
- live qpos を足すと transport / viewer の接続面が広がる
- 現時点では future issue として切り出したほうが安全である

## Remaining risk

- static fixture が backend の最新挙動に追従しなくなる可能性がある
- browser の scene update は `mjv_updateScene` と geometry cache の扱いに依存する
- production viewer への統合はこの issue の範囲外である

## Next issue

次に扱う候補:

1. live WebSocket payload に qpos を渡す専用の future issue
2. WASM scene viewer の camera / lighting / material hardening
3. fixture の追加 preset 化
