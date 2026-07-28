"""Fixed discovery entry point for replay_mapping/v1."""

from .implementation import REPLAY_CONTROL_MAPPING_PLUGIN


CONTROL_MAPPING_PLUGIN = REPLAY_CONTROL_MAPPING_PLUGIN

__all__ = ["CONTROL_MAPPING_PLUGIN"]
