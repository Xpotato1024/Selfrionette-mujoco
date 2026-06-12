"""Runtime composition root."""

from __future__ import annotations

from selfrionette.runtime.config import RuntimeConfig
from selfrionette.runtime.mujoco_pipeline import build_mujoco_pipeline
from selfrionette.runtime.pipeline import RuntimePipeline, build_noop_pipeline

__all__ = ["RuntimeConfig", "RuntimePipeline", "build_noop_pipeline", "build_mujoco_pipeline"]
