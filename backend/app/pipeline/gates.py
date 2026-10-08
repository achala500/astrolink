"""Star quality gating modules for astrophotography frames.

Provides star eccentricity validation (wind jitter detection),
star FWHM computation, and rolling FWHM tracking for optical blur detection.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator, Tuple

import cv2
import numpy as np


@dataclass
class GateResult:
    """Result of a quality gate evaluation with dual boolean and tuple compatibility."""

    passed: bool
    value: float
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed

    def __iter__(self) -> Iterator[Any]:
        yield self.passed
        yield self.value


def _normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    """Safely converts an input image to uint8 for contour analysis."""
    if image.dtype == np.uint8:
        return image.copy()

    img = image.astype(np.float32)
    # Performance optimization: strided subsampling [::4, ::4] on large frames (>=512x512)
    # speeds up global percentile calculations (~15x speedup).
    sample = img[::4, ::4] if img.shape[0] >= 512 and img.shape[1] >= 512 else img
    min_val = float(np.percentile(sample, 1))
    max_val = float(np.percentile(sample, 99.9))

    if max_val <= min_val:
        min_val, max_val = float(np.min(img)), float(np.max(img))

    if max_val > min_val:
        scaled = np.clip((img - min_val) / (max_val - min_val) * 255.0, 0, 255)
        return scaled.astype(np.uint8)
    return np.zeros(img.shape, dtype=np.uint8)


def check_star_eccentricity(
    gray: np.ndarray,
    max_eccentricity: float = 0.60,
    min_stars: int = 3,
) -> GateResult:
    """Fits ellipses to detected stars via contours and evaluates eccentricity.

    Computes e = sqrt(1 - (b / a)^2) where a and b are semi-major and semi-minor axes.
    Rejects frames with oblong/smeared stars caused by wind jitter or tracking error.

    Args:
        gray: 2D grayscale image array (uint8, uint16, or float).
        max_eccentricity: Upper limit of allowable median eccentricity (0 to 1).
        min_stars: Minimum number of detected stars required to evaluate frame.

    Returns:
        GateResult indicating if the frame passed, median eccentricity, and metrics.
    """
    if gray.ndim != 2:
        raise ValueError(f"Expected 2D grayscale image, got shape {gray.shape}")

    u8 = _normalize_to_uint8(gray)

    # Threshold stars using adaptive background estimation
    # Performance optimization: strided subsampling [::4, ::4] on large frames (>=512x512)
    # speeds up median and MAD background estimation (~15x speedup).
    sample = u8[::4, ::4] if u8.shape[0] >= 512 and u8.shape[1] >= 512 else u8
    bg_median = float(np.median(sample))
    bg_mad = float(np.median(np.abs(sample - bg_median)))
    thresh_val = int(min(254, max(15, bg_median + 2.5 * max(1.0, 1.4826 * bg_mad))))

    _, binary = cv2.threshold(u8, thresh_val, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    eccentricities: list[float] = []

    for cnt in contours:
        # cv2.fitEllipse requires at least 5 points
        if len(cnt) < 5:
            continue

        area = cv2.contourArea(cnt)
        if area < 4 or area > 5000:
            continue

        try:
            ellipse = cv2.fitEllipse(cnt)
            (_, _), (d1, d2), _ = ellipse
            major = max(d1, d2) / 2.0
            minor = min(d1, d2) / 2.0

            if major < 0.5:
                continue

            ratio = min(1.0, minor / major)
            e = float(np.sqrt(max(0.0, 1.0 - (ratio**2))))
            eccentricities.append(e)
        except cv2.error:
            continue

    if len(eccentricities) < min_stars:
        # Not enough stars detected to reliably confirm jitter; check if frame has valid stars
        return GateResult(
            passed=False,
            value=1.0,
            details={
                "star_count": len(eccentricities),
                "reason": "Insufficient stars detected for eccentricity assessment",
            },
        )

    median_ecc = float(np.median(eccentricities))
    mean_ecc = float(np.mean(eccentricities))
    passed = median_ecc <= max_eccentricity

    return GateResult(
        passed=passed,
        value=median_ecc,
        details={
            "star_count": len(eccentricities),
            "median_eccentricity": median_ecc,
            "mean_eccentricity": mean_ecc,
            "max_eccentricity_threshold": max_eccentricity,
        },
    )


def compute_fwhm(crop: np.ndarray) -> float:
    """Computes the Full Width at Half Maximum (FWHM) diameter of a target star.

    Uses 2D moment-based dispersion estimation calibrated to a Gaussian point
    spread function: FWHM = 2 * sqrt(2 * ln(2)) * sigma ≈ 2.35482 * sigma.

    Args:
        crop: 2D image sub-array centered on a star.

    Returns:
        FWHM diameter in pixels.
    """
    if crop.ndim != 2:
        raise ValueError(f"Expected 2D crop array, got shape {crop.shape}")

    arr = crop.astype(np.float64)
    h, w = arr.shape

    # Robust local background estimation using perimeter boundary pixels
    border_pixels = np.concatenate(
        [arr[0, :], arr[-1, :], arr[:, 0], arr[:, -1]]
    )
    bg = float(np.median(border_pixels))
    sub = np.maximum(0.0, arr - bg)

    total_flux = float(np.sum(sub))
    if total_flux <= 1e-6:
        return 0.0

    y_indices, x_indices = np.indices((h, w), dtype=np.float64)
    x_cen = float(np.sum(x_indices * sub) / total_flux)
    y_cen = float(np.sum(y_indices * sub) / total_flux)

    var_x = float(np.sum(((x_indices - x_cen) ** 2) * sub) / total_flux)
    var_y = float(np.sum(((y_indices - y_cen) ** 2) * sub) / total_flux)

    # Effective isotropic sigma
    sigma = np.sqrt(max(0.01, (var_x + var_y) / 2.0))
    fwhm = float(2.3548200450309493 * sigma)
    return fwhm


class RollingFWHMTracker:
    """Tracks star FWHM across a rolling window and detects optical blur drift.

    Maintains a deque(maxlen=5). If an incoming FWHM expands >25% above the baseline
    average of preceding measurements, triggers an optical blur alert (dew or focus drift).
    """

    def __init__(self, maxlen: int = 5, blur_threshold_ratio: float = 0.25):
        self.history: deque[float] = deque(maxlen=maxlen)
        self.blur_threshold_ratio = blur_threshold_ratio
        self.last_alert: bool = False
        self.last_ratio: float = 0.0

    def add_measurement(self, fwhm: float) -> Tuple[bool, float, str]:
        """Adds a new FWHM measurement and checks for blur condition.

        Args:
            fwhm: Incoming star FWHM in pixels.

        Returns:
            Tuple of (is_alert, baseline_fwhm, message).
        """
        fwhm_val = float(fwhm)

        if len(self.history) < 2:
            self.history.append(fwhm_val)
            self.last_alert = False
            self.last_ratio = 0.0
            return False, fwhm_val, "Baseline initializing"

        baseline = float(np.mean(self.history))
        expansion_ratio = (fwhm_val - baseline) / max(1e-4, baseline)
        self.last_ratio = expansion_ratio

        is_alert = expansion_ratio > self.blur_threshold_ratio
        self.last_alert = is_alert

        # Update history with current reading
        self.history.append(fwhm_val)

        if is_alert:
            msg = (
                f"Optical blur alert: FWHM expanded by {expansion_ratio * 100:.1f}% "
                f"(current: {fwhm_val:.2f}px, baseline: {baseline:.2f}px) - thermal/dew drift"
            )
        else:
            msg = f"FWHM nominal: {fwhm_val:.2f}px (baseline: {baseline:.2f}px)"

        return is_alert, baseline, msg

    def is_alert_active(self) -> bool:
        """Returns True if the most recent measurement triggered an alert."""
        return self.last_alert

    def get_baseline(self) -> float:
        """Returns the mean of the stored history."""
        if not self.history:
            return 0.0
        return float(np.mean(self.history))
