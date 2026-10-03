"""Astrophotography processing pipeline module.

Provides universal sub-exposure ingestion, quality gating, satellite streak masking,
star registration/alignment, constant-RAM streaming Welford sigma-clipped stacking,
background gradient removal, and MTF / Arcsinh display stretching.
"""

from backend.app.pipeline.alignment import FrameRejectedError, align_frame
from backend.app.pipeline.gates import (
    GateResult,
    RollingFWHMTracker,
    check_star_eccentricity,
    compute_fwhm,
)
from backend.app.pipeline.gradient import remove_background_gradient
from backend.app.pipeline.ingest import load_universal_frame
from backend.app.pipeline.satellites import detect_satellite_streaks
from backend.app.pipeline.stacker import WelfordStacker
from backend.app.pipeline.stretch import auto_stretch

__all__ = [
    "load_universal_frame",
    "check_star_eccentricity",
    "compute_fwhm",
    "RollingFWHMTracker",
    "GateResult",
    "detect_satellite_streaks",
    "align_frame",
    "FrameRejectedError",
    "WelfordStacker",
    "remove_background_gradient",
    "auto_stretch",
]
