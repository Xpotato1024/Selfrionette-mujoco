"""Fixed discovery entry point for loadcell_endpoint_mapping/v1."""

from .implementation import LOADCELL_ENDPOINT_MAPPING_PLUGIN


CONTROL_MAPPING_PLUGIN = LOADCELL_ENDPOINT_MAPPING_PLUGIN

__all__ = ["CONTROL_MAPPING_PLUGIN"]
