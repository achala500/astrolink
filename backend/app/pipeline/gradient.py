"""Background gradient and light pollution extraction module.

Models spatial skyglow gradients using downsampled star-masked robust statistics
and fits a 2nd-degree bivariate polynomial surface via least-squares optimization.
Subtracts the gradient surface while preserving background pedestal levels.
"""

from __future__ import annotations

import cv2
import numpy as np


def _build_bivariate_poly_features(x: np.ndarray, y: np.ndarray, order: int = 2) -> np.ndarray:
    """Builds polynomial basis terms for 2D coordinates up to specified order.

    For order=2: [1, x, y, x^2, x*y, y^2].
    """
    x_flat = x.ravel()
    y_flat = y.ravel()
    terms: list[np.ndarray] = []

    for total_deg in range(order + 1):
        for i in range(total_deg + 1):
            j = total_deg - i
            term = (x_flat**i) * (y_flat**j)
            terms.append(term)

    return np.column_stack(terms)


def _process_single_channel_gradient(
    channel_float: np.ndarray,
    order: int = 2,
    downsample_dim: int = 128,
) -> np.ndarray:
    """Fits and subtracts polynomial background gradient from a single channel."""
    h, w = channel_float.shape

    # Downsample for computational efficiency and high-frequency star suppression
    scale = min(1.0, float(downsample_dim) / max(h, w))
    down_w = max(16, int(round(w * scale)))
    down_h = max(16, int(round(h * scale)))

    downsampled = cv2.resize(channel_float, (down_w, down_h), interpolation=cv2.INTER_AREA)

    # Robust background estimation via Median and MAD
    med = float(np.median(downsampled))
    mad = float(np.median(np.abs(downsampled - med)))
    sigma = float(max(1e-6, 1.4826 * mad))

    # Mask stars: exclude pixels > median + 1.5 * sigma
    star_mask = downsampled > (med + 1.5 * sigma)
    # Also exclude dead pixels or extreme black borders
    black_mask = downsampled < (med - 3.0 * sigma)
    valid_bg = ~(star_mask | black_mask)

    if np.sum(valid_bg) < 20:
        # Fallback if almost everything was masked
        valid_bg = np.ones((down_h, down_w), dtype=bool)

    # Normalized coordinate grid [-1, 1] to ensure well-conditioned matrix
    y_coords, x_coords = np.mgrid[0:down_h, 0:down_w]
    x_norm = (2.0 * x_coords / max(1, down_w - 1)) - 1.0
    y_norm = (2.0 * y_coords / max(1, down_h - 1)) - 1.0

    features = _build_bivariate_poly_features(x_norm, y_norm, order=order)
    z_samples = downsampled.ravel()

    # Solve least-squares: A * c = z
    a_valid = features[valid_bg.ravel()]
    z_valid = z_samples[valid_bg.ravel()]

    coeffs, _, _, _ = np.linalg.lstsq(a_valid, z_valid, rcond=None)

    # Evaluate fitted background model across full image resolution
    y_full, x_full = np.mgrid[0:h, 0:w]
    x_full_norm = (2.0 * x_full / max(1, w - 1)) - 1.0
    y_full_norm = (2.0 * y_full / max(1, h - 1)) - 1.0

    full_features = _build_bivariate_poly_features(x_full_norm, y_full_norm, order=order)
    background_model = (full_features @ coeffs).reshape(h, w)

    # Pedestal level: preserve the median background level so shadows are not clipped
    pedestal = float(np.median(background_model))

    # Subtraction with pedestal preservation
    corrected = channel_float - background_model + pedestal
    return np.maximum(0.0, corrected).astype(np.float32)


def remove_background_gradient(
    image_float32: np.ndarray,
    order: int = 2,
    downsample_dim: int = 128,
) -> np.ndarray:
    """Removes light pollution gradients via 2nd-degree bivariate polynomial fitting.

    Downsamples the input image, masks stars using a robust (median + 1.5*sigma)
    threshold, fits a bivariate polynomial surface with np.linalg.lstsq,
    and subtracts the modeled gradient while maintaining background pedestal levels.

    Args:
        image_float32: Input image (2D grayscale or 3D color) in float32.
        order: Degree of the bivariate polynomial surface (default 2).
        downsample_dim: Dimension to which the image is resized for fitting.

    Returns:
        Gradient-subtracted image in float32 with preserved pedestal levels.
    """
    img = image_float32.astype(np.float32, copy=False)

    if img.ndim == 2:
        return _process_single_channel_gradient(img, order=order, downsample_dim=downsample_dim)

    if img.ndim == 3:
        channels: list[np.ndarray] = []
        for c in range(img.shape[2]):
            ch_clean = _process_single_channel_gradient(
                img[:, :, c],
                order=order,
                downsample_dim=downsample_dim,
            )
            channels.append(ch_clean)
        return np.stack(channels, axis=2)

    raise ValueError(f"Expected 2D or 3D image, got shape {img.shape}")
