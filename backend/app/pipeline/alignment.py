"""Star alignment and registration module for astrophotography frames.

Employs ORB feature detection, Hamming-distance brute-force matching,
and RANSAC homography to warp target frames into reference alignment.
Rejects frames compromised by cloud coverage or insufficient star matches.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

import cv2
import numpy as np


class FrameRejectedError(ValueError):
    """Exception raised when an astrophotography frame fails alignment validation."""

    pass


def _extract_gray_u8(image: np.ndarray) -> np.ndarray:
    """Extracts a normalized 8-bit single-channel image for feature tracking."""
    if image.ndim == 3:
        if image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY if image.dtype == np.uint8 else cv2.COLOR_RGB2GRAY)
        elif image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            gray = image[:, :, 0]
    else:
        gray = image

    if gray.dtype == np.uint8:
        return gray.copy()

    img = gray.astype(np.float32)
    # Strided subsampling on large images to accelerate global percentile estimation
    sample = img[::4, ::4] if img.shape[0] >= 512 and img.shape[1] >= 512 else img
    p_low = float(np.percentile(sample, 1))
    p_high = float(np.percentile(sample, 99.8))

    if p_high <= p_low:
        p_low, p_high = float(np.min(img)), float(np.max(img))

    if p_high > p_low:
        scaled = np.clip((img - p_low) / (p_high - p_low) * 255.0, 0.0, 255.0)
        return scaled.astype(np.uint8)

    return np.zeros(gray.shape[:2], dtype=np.uint8)


def count_stars(image: np.ndarray) -> int:
    """Estimates detectable star count via background thresholding and contour analysis."""
    u8 = _extract_gray_u8(image)
    med_sample = u8[::4, ::4] if u8.shape[0] >= 512 and u8.shape[1] >= 512 else u8
    med = float(np.median(med_sample))
    mad = float(np.median(np.abs(med_sample - med)))
    thresh_val = int(min(254, max(10, med + 3.0 * max(1.0, 1.4826 * mad))))
    _, binary = cv2.threshold(u8, thresh_val, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    stars = [c for c in contours if 3 <= cv2.contourArea(c) <= 3000]
    return len(stars)


def align_frame(
    ref_frame: np.ndarray,
    new_frame: np.ndarray,
    max_features: int = 1500,
    min_matches: int = 10,
    max_star_drop_ratio: float = 0.40,
    return_homography: bool = False,
) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
    """Aligns new_frame to ref_frame using ORB and RANSAC homography.

    Extracts up to 1500 ORB features and matches descriptors using BFMatcher
    with Hamming distance. Rejects frames with fewer than 10 good matches or
    if detected star count drops >40% relative to the reference frame (cloud detection).
    Warps new_frame to match ref_frame perspective.

    Args:
        ref_frame: Reference anchor image (2D or 3D, any numeric dtype).
        new_frame: Target image to register and warp onto ref_frame coordinates.
        max_features: Maximum ORB features to detect (default 1500).
        min_matches: Minimum valid cross-checked matches required (default 10).
        max_star_drop_ratio: Maximum allowable drop in star count (default 0.40).
        return_homography: If True, returns (warped_frame, H_matrix).

    Returns:
        Warped frame matching ref_frame dimensions, or (warped_frame, H)
        if return_homography is True.

    Raises:
        FrameRejectedError: If star count drops >40%, matches < 10, or homography fails.
    """
    ref_u8 = _extract_gray_u8(ref_frame)
    new_u8 = _extract_gray_u8(new_frame)

    # Rejection Gate 1: Star count drop > 40% (clouds, thick fog, dew)
    # Pass pre-extracted uint8 arrays directly to avoid redundant grayscale conversion
    n_ref_stars = count_stars(ref_u8)
    n_new_stars = count_stars(new_u8)

    if n_ref_stars > 0:
        star_drop = (n_ref_stars - n_new_stars) / float(n_ref_stars)
        if star_drop > max_star_drop_ratio:
            raise FrameRejectedError(
                f"Frame rejected: star count dropped by {star_drop * 100:.1f}% "
                f"({n_new_stars} vs {n_ref_stars} in reference, limit: {max_star_drop_ratio * 100:.0f}%) - cloud occlusion detected."
            )

    orb = cv2.ORB_create(nfeatures=max_features)
    kp_ref, desc_ref = orb.detectAndCompute(ref_u8, None)
    kp_new, desc_new = orb.detectAndCompute(new_u8, None)

    n_ref = len(kp_ref)
    n_new = len(kp_new)

    if n_ref == 0:
        raise FrameRejectedError("Reference frame contains 0 detectable star features.")

    if desc_ref is None or desc_new is None or n_new == 0:
        raise FrameRejectedError(f"Insufficient descriptors found (new: {n_new}, ref: {n_ref}).")

    # Match descriptors using Hamming distance
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(desc_ref, desc_new)

    # Sort matches by distance
    matches = sorted(matches, key=lambda m: m.distance)

    # Rejection Gate 2: Matches < 10
    if len(matches) < min_matches:
        raise FrameRejectedError(
            f"Frame rejected: only {len(matches)} star matches found "
            f"(minimum required: {min_matches})."
        )

    # Extract matched point coordinates
    # queryIdx corresponds to ref_frame, trainIdx corresponds to new_frame
    src_pts = np.float32([kp_new[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_ref[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)

    # Compute 3x3 Homography matrix with RANSAC
    H, inlier_mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if H is None:
        raise FrameRejectedError("Frame rejected: RANSAC homography estimation failed.")

    inliers = int(np.sum(inlier_mask)) if inlier_mask is not None else 0
    if inliers < min_matches:
        raise FrameRejectedError(
            f"Frame rejected: insufficient RANSAC inliers ({inliers} < {min_matches})."
        )

    h_ref, w_ref = ref_frame.shape[:2]

    # Warp new_frame to match reference frame
    warped = cv2.warpPerspective(
        new_frame,
        H,
        (w_ref, h_ref),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    if return_homography:
        return warped, H
    return warped
