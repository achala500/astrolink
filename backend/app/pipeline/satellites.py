"""Satellite streak detection module for astrophotography frames.

Identifies linear satellite and aircraft trails using edge detection and
probabilistic Hough transforms, generating exclusion masks for stacking.
"""

from __future__ import annotations

import cv2
import numpy as np


def _to_uint8(image: np.ndarray) -> np.ndarray:
    """Normalizes an image of arbitrary scalar type to uint8."""
    if image.dtype == np.uint8:
        return image.copy()

    img = image.astype(np.float32)
    p_low = float(np.percentile(img, 1))
    p_high = float(np.percentile(img, 99.8))

    if p_high <= p_low:
        p_low, p_high = float(np.min(img)), float(np.max(img))

    if p_high > p_low:
        scaled = np.clip((img - p_low) / (p_high - p_low) * 255.0, 0.0, 255.0)
        return scaled.astype(np.uint8)

    return np.zeros(img.shape, dtype=np.uint8)


def detect_satellite_streaks(
    gray: np.ndarray,
    min_line_length: int = 150,
    max_line_gap: int = 30,
    canny_thresh1: int = 30,
    canny_thresh2: int = 100,
    dilation_px: int = 5,
) -> np.ndarray:
    """Detects satellite and plane streaks across a grayscale sub-exposure.

    Runs Canny edge detection followed by the Probabilistic Hough Line Transform
    (HoughLinesP). Detected continuous lines exceeding min_line_length are drawn
    and dilated by dilation_px to account for the streak point-spread wings.

    Args:
        gray: 2D grayscale image array (uint8, uint16, or float).
        min_line_length: Minimum streak line length in pixels (default 150px).
        max_line_gap: Maximum allowable gap in pixels between collinear segments.
        canny_thresh1: Lower threshold for Canny edge detector.
        canny_thresh2: Upper threshold for Canny edge detector.
        dilation_px: Radius in pixels by which detected streak lines are dilated.

    Returns:
        Binary boolean mask (shape matching gray, dtype=bool) where True
        denotes streak pixels to exclude from stacking.
    """
    if gray.ndim != 2:
        raise ValueError(f"Expected 2D grayscale image, got shape {gray.shape}")

    h, w = gray.shape
    u8 = _to_uint8(gray)

    # Mild blur to suppress high-frequency shot noise without blunting linear streaks
    blurred = cv2.GaussianBlur(u8, (3, 3), 0)

    # Edge detection
    edges = cv2.Canny(blurred, canny_thresh1, canny_thresh2, apertureSize=3)

    # Probabilistic Hough Line Transform
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )

    streak_mask = np.zeros((h, w), dtype=np.uint8)

    if lines is not None:
        for line in lines.reshape(-1, 4):
            x1, y1, x2, y2 = line
            dx = float(x2 - x1)
            dy = float(y2 - y1)
            length = np.hypot(dx, dy)

            if length >= min_line_length:
                # Draw the line segment
                cv2.line(streak_mask, (int(x1), int(y1)), (int(x2), int(y2)), 255, thickness=2)

    # Dilate detected lines by specified radius to cover star-forming streak wings
    if np.any(streak_mask > 0):
        kernel_size = 2 * dilation_px + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated = cv2.dilate(streak_mask, kernel, iterations=1)
        return dilated > 0

    return np.zeros((h, w), dtype=bool)
