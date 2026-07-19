"""First-party versioned input source plugins."""

from selfrionette.plugins.input_sources.catalog import (
    INPUT_SOURCE_CATALOG,
    INPUT_SOURCE_PLUGIN_REGISTRY,
    SUPPORTED_INPUT_SOURCE_NAMES,
    get_input_source_registration,
    resolve_input_source_plugin,
)

__all__ = [
    "INPUT_SOURCE_CATALOG",
    "INPUT_SOURCE_PLUGIN_REGISTRY",
    "SUPPORTED_INPUT_SOURCE_NAMES",
    "get_input_source_registration",
    "resolve_input_source_plugin",
]
