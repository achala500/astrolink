"""Nonlinear Midtone Transfer Function (MTF) display stretch module.

Implements the vectorized PixInsight MTF algorithm using Median Absolute Deviation (MAD)
to transform linear 16/32-bit astronomical data into crisp 8-bit display previews.
Features an Arcsinh stretch mode for stellar chromaticity and saturation preservation.
"""

from __future__ import annotations

import numpy as np


def _apply_mtf(x: np.ndarray, m: float) -> np.ndarray:
    """Vectorized PixInsight Midtone Transfer Function (MTF).

    MTF(x, m) = (m - 1) * x / ((2*m - 1) * x - m)
    """
    m = float(np.clip(m, 1e-4, 1.0 - 1e-4))
    x_clip = np.clip(x, 0.0, 1.0)

    numer = (m - 1.0) * x_clip
    denom = (2.0 * m - 1.0) * x_clip - m

    # Prevent division by zero at boundary points
    mask_zero = np.abs(denom) < 1e-9
    out = np.zeros_like(x_clip)
    valid = ~mask_zero
    out[valid] = numer[valid] / denom[valid]

    # Explicit boundaries
    out[x_clip <= 0.0] = 0.0
    out[x_clip >= 1.0] = 1.0
    return np.clip(out, 0.0, 1.0)


def _compute_mtf_parameters(
    channel: np.ndarray,
    target_bg: float = 0.25,
    shadow_clip_k: float = -2.8,
) -> tuple[float, float, float]:
    """Computes robust shadow clipping point and midtone balance parameter m."""
    # Performance optimization: strided subsampling [::4, ::4] on large frames (>=512x512)
    # reduces median/MAD sorting overhead from ~12M elements to ~750k elements (~15x speedup).
    if channel.ndim >= 2 and channel.shape[0] >= 512 and channel.shape[1] >= 512:
        sample = channel[::4, ::4]
    else:
        sample = channel

    med = float(np.median(sample))
    mad = float(np.median(np.abs(sample - med)))
    sigma = float(max(1e-6, 1.4826 * mad))

    # Shadow clipping point c0 (PixInsight default: median - 2.8 * sigma)
    c0 = max(0.0, med + shadow_clip_k * sigma)
    c1 = float(np.max(channel))
    if c1 <= c0:
        c1 = c0 + 1.0

    # Normalized median position relative to shadow clipping
    x_med = float(np.clip((med - c0) / (c1 - c0), 1e-5, 1.0 - 1e-5))
    target = float(np.clip(target_bg, 1e-3, 1.0 - 1e-3))

    # Solve MTF(x_med, m) = target_bg for m:
    # m = x_med * (1 - target) / (x_med * (1 - 2*target) + target)
    denom = x_med * (1.0 - 2.0 * target) + target
    if abs(denom) < 1e-7:
        m = 0.5
    else:
        m = (x_med * (1.0 - target)) / denom
    m = float(np.clip(m, 1e-4, 1.0 - 1e-4))

    return c0, c1, m


def auto_stretch(
    image_float32: np.ndarray,
    target_bg: float = 0.25,
    preserve_saturation: bool = False,
    asinh_factor: float = 100.0,
) -> np.ndarray:
    """Converts linear 16/32-bit astrophotography frames to crisp 8-bit display previews.

    Uses the vectorized PixInsight Midtone Transfer Function (MTF) algorithm
    grounded in Median Absolute Deviation (MAD). When preserve_saturation is True
    on 3-channel color data, applies an Arcsinh stretch (Lupton et al.) to preserve
    stellar chromaticity and prevent star cores from washing out to white.

    Args:
        image_float32: Input linear image (2D grayscale or 3D color) in float32.
        target_bg: Target background brightness level (default 0.25, i.e., 25% gray).
        preserve_saturation: If True, uses Arcsinh luminance stretch on color images.
        asinh_factor: Stretch strength factor for Arcsinh mapping (default 100.0).

    Returns:
        Crisp 8-bit display preview image (uint8, [0, 255]).
    """
    img = image_float32.astype(np.float32, copy=False)

    if img.ndim == 2:
        c0, c1, m = _compute_mtf_parameters(img, target_bg=target_bg)
        norm = np.clip((img - c0) / (c1 - c0), 0.0, 1.0)
        stretched = _apply_mtf(norm, m)
        return (stretched * 255.0).astype(np.uint8)

    if img.ndim == 3:
        if preserve_saturation:
            # Saturation-preserving Arcsinh Stretch (Lupton et al. 2004)
            # Compute luminance across color channels
            if img.shape[2] == 3:
                # Rec.709 photometric weights
                lum = 0.2126 * img[:, :, 0] + 0.7152 * img[:, :, 1] + 0.0722 * img[:, :, 2]
            else:
                lum = np.mean(img, axis=2)

            c0, c1, _ = _compute_mtf_parameters(lum, target_bg=target_bg)
            lum_norm = np.clip((lum - c0) / (c1 - c0), 0.0, 1.0)

            # Arcsinh stretch function: S(L) = asinh(a * L) / asinh(a)
            beta = max(1.0, float(asinh_factor))
            asinh_denom = float(np.arcsinh(beta))
            stretched_lum = np.arcsinh(beta * lum_norm) / asinh_denom

            # Apply midtone alignment to target background
            med_lum = float(np.median(stretched_lum))
            if med_lum > 1e-4:
                scale_to_bg = target_bg / med_lum
                stretched_lum = np.clip(stretched_lum * scale_to_bg, 0.0, 1.0)

            # Scale channels by luminance ratio to preserve chromaticity (R:G:B)
            scale_factor = np.zeros_like(lum_norm)
            valid_lum = lum_norm > 1e-6
            scale_factor[valid_lum] = stretched_lum[valid_lum] / lum_norm[valid_lum]

            out_channels = []
            for c in range(img.shape[2]):
                ch_norm = np.clip((img[:, :, c] - c0) / (c1 - c0), 0.0, 1.0)
                ch_stretched = np.clip(ch_norm * scale_factor, 0.0, 1.0)
                out_channels.append(ch_stretched)

            stacked_stretched = np.stack(out_channels, axis=2)
            return (stacked_stretched * 255.0).astype(np.uint8)
        else:
            # Linked/Unlinked MTF stretch across channels
            out_channels = []
            for c in range(img.shape[2]):
                ch = img[:, :, c]
                c0, c1, m = _compute_mtf_parameters(ch, target_bg=target_bg)
                norm = np.clip((ch - c0) / (c1 - c0), 0.0, 1.0)
                ch_stretched = _apply_mtf(norm, m)
                out_channels.append(ch_stretched)

            stacked_stretched = np.stack(out_channels, axis=2)
            return (stacked_stretched * 255.0).astype(np.uint8)

    raise ValueError(f"Expected 2D or 3D image, got shape {img.shape}")
