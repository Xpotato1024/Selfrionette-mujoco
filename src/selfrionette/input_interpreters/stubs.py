from __future__ import annotations

from selfrionette.input_interpreters.base import InputInterpreter
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


# Keep the contract import available for explicit, module-local imports.
__all__ = ["NoOpInputInterpreter"]
