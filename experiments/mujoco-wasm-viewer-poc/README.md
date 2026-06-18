# MuJoCo WASM Viewer PoC

`@mujoco/mujoco` を使って `assets/mujoco/fast_arm/scene.xml` を browser 上で扱う isolated PoC です。

## Scope

- official MuJoCo WASM bindings の読み込み
- `scene.xml` / `arm.xml` / STL mesh の読み込み
- `home` keyframe の適用
- Python native MuJoCo 由来の qpos fixture の読み込み
- WASM 側 `data.qpos` への frame qpos の適用
- `mj_forward` / `mjv_updateScene` 後の scene geom 再描画
- 最小の playback controls

## Non-goals

- `apps/mujoco-viewer` の変更
- production viewer integration
- backend / runtime / motion / IK / FK の behavior change
- browser-side qpos recompute
- payload schema change

## Run

```powershell
cd experiments\mujoco-wasm-viewer-poc
npm ci
npm run dev -- --host 127.0.0.1 --port 4173
```

Open:

```text
http://127.0.0.1:4173/experiments/mujoco-wasm-viewer-poc/
```

## Fixture generation

The fixture is generated from the native MuJoCo dry-run path and written into the PoC public fixture directory.

```powershell
cd D:\Xpotato-apps\Selfrionette-mujoco
uv run python scripts/export_wasm_qpos_fixture.py --preset sweep_x --steps 30 --output experiments/mujoco-wasm-viewer-poc/public/fixtures/fast_arm_sweep_x_qpos.json
```

Fixture output:

```text
experiments/mujoco-wasm-viewer-poc/public/fixtures/fast_arm_sweep_x_qpos.json
```

## Playback

- `Load fixture` reads the generated JSON fixture.
- `Play` advances through fixture frames.
- `Pause` stops the timer.
- `Step next` and `Step previous` move one frame at a time.
- `Reset to home` reapplies the MuJoCo `home` keyframe.

## Boundary

- Python native MuJoCo remains the source of truth.
- Browser WASM MuJoCo is a visual renderer candidate only.
- Browser-side IK / FK / qpos recompute is not performed.

## Fixture schema

The PoC expects:

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

## Current limitations

- The fixture is loaded from a static JSON file rather than a live transport stream.
- Live WebSocket qpos sync is not implemented in this PoC.
- The viewer remains isolated from production viewer code and dependencies.
- Visual fidelity is limited to the current asset and scene setup.
