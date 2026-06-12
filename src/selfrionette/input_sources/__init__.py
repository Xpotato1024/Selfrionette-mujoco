from __future__ import annotations

from selfrionette.input_sources.base import InputSource
from selfrionette.input_sources.replay import ReplayInputSource
from selfrionette.input_sources.stubs import StaticInputSource

__all__ = ["InputSource", "ReplayInputSource", "StaticInputSource"]
