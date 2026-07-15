# R6-K-P2 MotionCommand Step Loop

## 目的

R6-K-P2 では、#247 で導入した input source registry の選択結果を
runtime の step loop に接続し、`RawInputFrame -> InputIntent ->
MotionCommand -> MuJoCo` の流れを local/dev runtime でそのまま動かす。
`desired_endpoint_m` は command-side endpoint のまま維持し、
`target_position_m` は viewer / feedback の互換フィールドとして扱う。

## 対象

- `src/selfrionette/runtime/input_step_loop.py`
- `scripts/run_replay_mujoco_websocket_publisher.py`
- `tests/runtime/test_motion_command_step_loop_integration.py`
- `tests/runtime/test_websocket_publisher_runner_programmed_input.py`

## 接続した内容

- `programmed_target` の選択結果を runtime loop へ渡した
- `MotionCommand.metadata["desired_endpoint_m"]` を優先して使った
- `target_position_m` は primary command にせず、feedback として更新した
- 既存の MuJoCo IK/FK と endpoint evaluation の流れをそのまま使った
- source 未選択時は replay の既存フォールバックを残した

## 除外

- browser input の新規実装
- live serial / COM / OSC / hardware access
- FK / IK の再設計
- frontend の再設計

## 検証

- `pytest` の対象 runtime テストで step loop の selected source / replay fallback / endpoint evaluation optional を確認する
- `git diff --check` で空白・改行の崩れを確認する
