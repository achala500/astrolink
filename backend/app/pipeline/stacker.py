"""Streaming astrophotography stacker using Welford's algorithm with sigma clipping.

Provides constant-memory (O(1) in frame count, <200MB) streaming accumulation of sub-exposures.
Features online 2.5-sigma outlier rejection (for cosmic rays and transient artifacts)
and satellite streak mask integration.
"""

from __future__ import annotations

import sys
from typing import Optional, Tuple

import numpy as np


class WelfordStacker:
    """Streaming 2.5-sigma clipped stacker using Welford's running statistics.

    Maintains per-pixel running mean and M2 sum of squared differences, enabling
    exact variance estimation on-the-fly without buffering past frames in RAM.
    Excludes satellite streaks and pixels that deviate by more than 2.5 standard deviations.
    """

    def __init__(
        self,
        shape: Optional[Tuple[int, ...]] = None,
        dtype: np.dtype = np.float32,
        sigma_clip: float = 2.5,
        min_samples_for_clip: int = 3,
    ):
        """Initializes the Welford streaming stacker.

        Args:
            shape: Expected image shape (e.g. (H, W) or (H, W, C)). If None,
                initialized from the first incoming frame.
            dtype: Floating point precision for accumulation (np.float32 or np.float64).
            sigma_clip: Multiplier for standard deviation outlier rejection (default 2.5).
            min_samples_for_clip: Number of frames before clipping engages.
        """
        self.shape = shape
        self.dtype = dtype
        self.sigma_clip = float(sigma_clip)
        self.min_samples_for_clip = int(min_samples_for_clip)

        self.mean: Optional[np.ndarray] = None
        self.m2: Optional[np.ndarray] = None
        self.counts: Optional[np.ndarray] = None
        self.total_frames_processed: int = 0

        if shape is not None:
            self._init_buffers(shape)

    def _init_buffers(self, shape: Tuple[int, ...]) -> None:
        """Allocates running state arrays."""
        self.shape = shape
        self.mean = np.zeros(shape, dtype=self.dtype)
        self.m2 = np.zeros(shape, dtype=self.dtype)
        self.counts = np.zeros(shape, dtype=np.uint32)

    def reset(self) -> None:
        """Resets accumulator state to zero."""
        if self.shape is not None:
            self._init_buffers(self.shape)
        else:
            self.mean = None
            self.m2 = None
            self.counts = None
        self.total_frames_processed = 0

    def add_frame(
        self,
        frame: np.ndarray,
        mask: Optional[np.ndarray] = None,
    ) -> int:
        """Accumulates a single sub-exposure into the running stack.

        Args:
            frame: Incoming aligned sub-exposure (2D or 3D).
            mask: Optional boolean mask where True indicates pixels to exclude
                (e.g., satellite streaks).

        Returns:
            Total count of frames fed to the stacker so far.
        """
        x = frame.astype(self.dtype, copy=False)

        if self.mean is None or self.counts is None or self.m2 is None:
            self._init_buffers(x.shape)

        if self.mean is None or self.counts is None or self.m2 is None:
            raise RuntimeError("Stacker internal state buffers were not initialized correctly.")

        # Mask of pixels to include
        if mask is not None:
            if mask.ndim == 2 and x.ndim == 3:
                # Expand 2D streak mask across color channels
                mask_expanded = np.repeat(mask[:, :, np.newaxis], x.shape[2], axis=2)
                valid = ~mask_expanded
            else:
                valid = ~mask.astype(bool)
        else:
            valid = np.ones(x.shape, dtype=bool)

        # 2.5-Sigma Clipping for pixels with sufficient history
        clip_candidates = (self.counts >= self.min_samples_for_clip) & valid
        if np.any(clip_candidates):
            # Sample variance: s^2 = M2 / (n - 1)
            var = np.zeros_like(self.m2)
            mask_has_var = self.counts > 1
            var[mask_has_var] = self.m2[mask_has_var] / (self.counts[mask_has_var] - 1)
            std = np.sqrt(np.maximum(0.0, var))

            diff = np.abs(x - self.mean)
            threshold = self.sigma_clip * std

            # In astrophotography, clipping also enforces a small floor on std to avoid
            # clipping when pixels have identical constant values
            min_noise_floor = 1e-4
            threshold = np.maximum(threshold, min_noise_floor)

            is_outlier = clip_candidates & (diff > threshold)
            # Exclude outliers from accumulation
            valid = valid & ~is_outlier

        # Vectorized Welford Update on valid pixels
        if np.any(valid):
            new_counts = self.counts + 1
            delta = x - self.mean
            # Update mean: mu_n = mu_{n-1} + delta / n
            new_mean = self.mean + (delta / new_counts.astype(self.dtype))
            delta2 = x - new_mean
            # Update M2: M2_n = M2_{n-1} + delta * delta2
            new_m2 = self.m2 + (delta * delta2)

            # Apply only to valid locations with strict dtype preservation
            self.mean = np.where(valid, new_mean.astype(self.dtype), self.mean)
            self.m2 = np.where(valid, new_m2.astype(self.dtype), self.m2)
            self.counts = np.where(valid, new_counts, self.counts)

        self.total_frames_processed += 1
        return self.total_frames_processed

    def get_result(self) -> np.ndarray:
        """Returns the current running mean stacked image."""
        if self.mean is None:
            raise ValueError("No frames have been stacked yet.")
        return self.mean.astype(self.dtype, copy=True)

    def get_variance(self) -> np.ndarray:
        """Returns the sample variance of accumulated pixels."""
        if self.m2 is None or self.counts is None:
            raise ValueError("No frames have been stacked yet.")
        var = np.zeros_like(self.m2)
        valid = self.counts > 1
        var[valid] = self.m2[valid] / (self.counts[valid] - 1)
        return var

    def get_std(self) -> np.ndarray:
        """Returns the sample standard deviation."""
        return np.sqrt(np.maximum(0.0, self.get_variance()))

    def get_counts(self) -> np.ndarray:
        """Returns the valid sample count per pixel."""
        if self.counts is None:
            raise ValueError("No frames have been stacked yet.")
        return self.counts.copy()

    def get_memory_usage_mb(self) -> float:
        """Calculates total RAM occupied by stacker buffers in Megabytes."""
        total_bytes = 0
        for arr in (self.mean, self.m2, self.counts):
            if arr is not None:
                total_bytes += arr.nbytes
        total_bytes += sys.getsizeof(self)
        return total_bytes / (1024.0 * 1024.0)
