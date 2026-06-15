# Summary
- P6 の runtime stub guardrail を追加し、`build_concrete_mujoco_pipeline()` を concrete default の正本として固定した。
- `run_replay_mujoco_dry_run()` と `run_replay_mujoco_websocket_publisher()` が production-like path で no-op / zero stub に戻らないことをテストで固定した。
- `sweep_x` は visual-smoke compatibility path としてのみ例外扱いを維持した。

Closes #122

# Changed Files
- `tests/runtime/test_runtime_stub_guardrails.py`
- `docs/operations/r6-h-p6-runtime-zero-stub-guardrail.md`
- `docs/operations/r6-h-p5-runtime-concrete-solver-wiring.md`
- `docs/architecture/runtime-composition.md`
- `docs/README.md`

# Architecture Impact
- runtime default / production-like path から `StaticInputSource`, `NoOpInputInterpreter`, `NoOpMotionGenerator`, `NoOpMuJoCoSimulator`, `NoOpStatePublisher`, `ZeroForwardKinematicsSolver`, `ZeroInverseKinematicsSolver` への再流入を guardrail で抑止した。
- `build_noop_pipeline()` は explicit placeholder / test path として維持し、production-like default とは分離した。
- `sweep_x` は compatibility exception として明示し、P7 completion audit への handoff を追加した。

# Validation
- `git diff --check`
- `uv run python -m compileall src tests`
- `uv run pytest tests/runtime/test_runtime_stub_guardrails.py tests/runtime/test_concrete_mujoco_pipeline.py tests/runtime/test_replay_mujoco_dry_run_entry.py tests/runtime/test_replay_mujoco_websocket_publisher.py tests/runtime/test_noop_pipeline.py tests/runtime/test_mujoco_pipeline.py tests/runtime/test_replay_mujoco_pipeline.py tests/stubs/test_layer_stubs.py tests/kinematics tests/motion tests/mujoco_backend tests/transport -q`
- `uv run python` による Japanese docs encoding check: passed

# Scope Exclusions
- viewer-side FK / IK / qpos recompute は追加していない。
- browser-side MuJoCo model loading は追加していない。
- schema breaking change は行っていない。
- hardware / serial / OSC は扱っていない。
- legacy import / execute は行っていない。
- package dependency change は行っていない。

# Hardware Validation
- 実施していない。

# Serial / OSC / Hardware Access
- serial port opened: no
- OSC sent: no
- hardware access: no

# Remaining Risks
- `build_noop_pipeline()` と `build_mujoco_pipeline()` は compatibility helper として残しているため、今後の変更では production-like default へ戻さないことを継続的に確認する必要がある。
- `mergeable` は GitHub 側の状態遷移に依存するため、PR 作成直後は `UNKNOWN` の場合がある。