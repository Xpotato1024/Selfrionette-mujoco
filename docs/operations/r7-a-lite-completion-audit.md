# R7-A-lite Completion Audit

## Parent

- Parent: `#152`

## 完了した child issues

- `#197` inventory / legacy firmware import / hardware bring-up docs
- `#198` serial frame contract
- `#199` parser fixture
- `#200` SerialInputSource skeleton
- `#201` loadcell raw -> normalized input intent
- `#202` normalized intent -> desired_endpoint_m
- `#203` recorded serial dry-run smoke
- `#204` WebSocket / viewer smoke and completion audit

## merged PR

- `#205`
- `#207`
- `#208`
- `#209`
- `#210`
- `#211`
- `#212`
- `#213`
- `#214`
- current PR

## 現時点で proven なこと

- legacy firmware reference is preserved
- hardware bring-up notes and generated evidence are preserved
- serial frame contract exists
- parser handles vector / status / warn / malformed frames
- `SerialInputSource` works with injected lines only
- raw 7ch values normalize deterministically
- normalized intent maps to `desired_endpoint_m` via configurable mapping
- offline fixture dry-run reaches `MotionCommand.metadata["desired_endpoint_m"]`
- WebSocket / viewer-facing smoke preserves command-side endpoint fields

## intentionally unproven のまま残すこと

- live serial automated run
- CI hardware access
- final physical axis mapping
- force unit conversion to `N/kg`
- MuJoCo live backend integration from serial
- WebSocket live streaming from COM port
- viewer actual browser visual confirmation
- actuator / real robot / OSC output
- robotics-grade IK/FK

## 次の推奨フェーズ

この PR が land したら `#152` を close する。live serial / hardware / browser / robotics-grade integration が必要なら、別の明示的 phase として切り出す。
