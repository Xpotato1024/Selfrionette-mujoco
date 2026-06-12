from __future__ import annotations

from selfrionette.schemas import InputIntent, RawInputFrame


class ReplayInputInterpreter:
    """Deterministic replay interpreter that preserves the raw frame payload."""

    def interpret(self, frame: RawInputFrame) -> InputIntent:
        return InputIntent(
            source=frame.source,
            timestamp_s=frame.timestamp_s,
            values=frame.values,
            buttons=frame.buttons,
            metadata=dict(frame.metadata),
        )


__all__ = ["ReplayInputInterpreter"]
