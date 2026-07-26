from __future__ import annotations

from selfrionette.plugins.mappings.replay import build_input_intent_from_replay_frame
from selfrionette.schemas import InputIntent, RawInputFrame


class ReplayInputInterpreter:
    """Deterministic replay interpreter that preserves raw replay payloads.

    Metadata is handled as a Mapping and copied shallowly. Nested metadata
    objects are intentionally not deep-copied.
    """

    def interpret(self, frame: RawInputFrame) -> InputIntent:
        return build_input_intent_from_replay_frame(frame)


__all__ = ["ReplayInputInterpreter"]
