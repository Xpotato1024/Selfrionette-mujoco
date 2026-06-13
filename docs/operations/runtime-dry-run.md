---
status: canonical
owner: architecture
last_verified: 2026-06-14
canonical_for:
  - runtime dry-run entry
related:
  - docs/architecture/runtime-composition.md
  - docs/architecture/data-flow.md
  - docs/contracts/transport-payload.md
---

# Runtime Dry-Run

R6-A-P3 adds a deterministic runtime dry-run entry for replay-driven payload
inspection.

## Command

```bash
uv run python scripts/run_replay_mujoco_dry_run.py --steps 1
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --dt-s 0.0166666667
uv run python scripts/run_replay_mujoco_dry_run.py --steps 3 --output /tmp/selfrionette_payload.ndjson
```

## Output

- stdout prints one payload v0 JSON object per line.
- `--output` writes the same NDJSON stream to a file.
- `version` stays `0`.
- `frame_index` increments per replay step.

## Scope

- The entry uses the runtime replay pipeline and the transport publisher
  skeleton.
- The entry does not open a WebSocket server.
- The entry does not launch the viewer.
- The entry does not open serial or OSC connections.

## Phase Note

Phase B can extend this dry-run path to viewer WebSocket connection work after
the runtime dry-run contract is stable.
