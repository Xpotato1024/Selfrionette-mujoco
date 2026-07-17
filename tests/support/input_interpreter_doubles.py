"""Test-only input interpreter doubles."""

from __future__ import annotations

from selfrionette.schemas import InputIntent, RawInputFrame


class NoOpInputInterpreter:
    """No-op input interpreter stub, not a real input processing pipeline."""

    def interpret(self, frame: RawInputFrame) -> InputIntent:
        return InputIntent(
            source=frame.source,
            timestamp_s=frame.timestamp_s,
            values=frame.values,
            target_delta_m=(0.0, 0.0, 0.0),
            joint_delta_rad=(),
            buttons=frame.buttons,
            metadata=dict(frame.metadata),
        )


__all__ = ["NoOpInputInterpreter"]
