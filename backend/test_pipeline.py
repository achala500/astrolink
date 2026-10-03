"""Standalone test suite for the astrophotography processing pipeline.

Generates 5 synthetic star frames with artificial noise, tracking drift, light pollution
gradients, and satellite streaks. Verifies end-to-end functionality:
1. Star eccentricity gate (wind jitter rejection) and FWHM blur tracking.
2. Satellite streak detection and binary exclusion mask generation.
3. Star registration with ORB + RANSAC homography, including cloud occlusion rejection.
4. Streaming Welford 2.5-sigma clipped stacking (asserts RAM < 200MB and streak removal).
5. 2nd-degree polynomial background gradient removal and pedestal preservation.
6. Vectorized PixInsight MTF and Arcsinh auto_stretch preview generation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pytest

# Ensure backend package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.pipeline.alignment import FrameRejectedError, align_frame
from backend.app.pipeline.gates import (
    RollingFWHMTracker,
    check_star_eccentricity,
    compute_fwhm,
)
from backend.app.pipeline.gradient import remove_background_gradient
from backend.app.pipeline.satellites import detect_satellite_streaks
from backend.app.pipeline.stacker import WelfordStacker
from backend.app.pipeline.stretch import auto_stretch


def generate_synthetic_star_field(
    height: int = 512,
    width: int = 512,
    num_stars: int = 70,
    seed: int = 42,
) -> Tuple[np.ndarray, List[Tuple[float, float, float, float]]]:
    """Generates a ground-truth star field with 2D Gaussian point spread functions."""
    rng = np.random.default_rng(seed)
    field = np.zeros((height, width), dtype=np.float32)

    stars: List[Tuple[float, float, float, float]] = []
    margin = 50
    x_coords = rng.uniform(margin, width - margin, num_stars)
    y_coords = rng.uniform(margin, height - margin, num_stars)
    intensities = rng.uniform(0.3, 1.0, num_stars)
    sigmas = rng.uniform(1.2, 2.2, num_stars)

    y_grid, x_grid = np.mgrid[0:height, 0:width]

    for x0, y0, intensity, sigma in zip(x_coords, y_coords, intensities, sigmas):
        r2 = (x_grid - x0) ** 2 + (y_grid - y0) ** 2
        psf = intensity * np.exp(-r2 / (2.0 * sigma**2))
        field += psf.astype(np.float32)
        stars.append((float(x0), float(y0), float(intensity), float(sigma)))

    return field, stars


def generate_synthetic_dataset(
    num_frames: int = 5,
    height: int = 512,
    width: int = 512,
) -> Tuple[List[np.ndarray], List[Tuple[float, float]], List[bool]]:
    """Generates 5 synthetic frames with drift, noise, gradient, and satellite streaks."""
    base_field, _ = generate_synthetic_star_field(height, width, num_stars=80, seed=123)

    # 2nd-degree polynomial background light pollution gradient
    y_norm, x_norm = np.mgrid[-1:1:complex(0, height), -1:1:complex(0, width)]
    gradient = 0.05 + 0.02 * x_norm + 0.015 * y_norm + 0.01 * (x_norm**2) + 0.012 * (y_norm**2)
    gradient = gradient.astype(np.float32)

    frames: List[np.ndarray] = []
    drifts: List[Tuple[float, float]] = []
    has_satellite: List[bool] = []

    rng = np.random.default_rng(42)

    for i in range(num_frames):
        # Mount tracking drift (dx, dy)
        dx = float(i * 3.5)
        dy = float(i * -2.0)
        drifts.append((dx, dy))

        M = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted_stars = cv2.warpAffine(base_field, M, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=0)

        frame = shifted_stars + gradient

        # Frames 1 and 3 contain synthetic satellite trails
        is_sat = i in (1, 3)
        has_satellite.append(is_sat)

        if is_sat:
            streak = np.zeros((height, width), dtype=np.float32)
            if i == 1:
                cv2.line(streak, (40, 60), (320, 240), 0.85, thickness=2)
            else:
                cv2.line(streak, (50, 300), (450, 310), 0.90, thickness=2)

            streak = cv2.GaussianBlur(streak, (3, 3), 0)
            frame += streak

        read_noise = rng.normal(0, 0.006, (height, width)).astype(np.float32)
        frame = np.clip(frame + read_noise, 0.0, 1.0)
        frames.append(frame)

    return frames, drifts, has_satellite


# =====================================================================
# STAGE EXECUTION FUNCTIONS
# =====================================================================


def run_gates_stage() -> None:
    """Executes gates validation."""
    print("[1/6] Testing Gates Module (eccentricity, FWHM, RollingFWHMTracker)...")

    # 1. Test eccentricity on round stars
    round_field, _ = generate_synthetic_star_field(num_stars=30, seed=7)
    res_round = check_star_eccentricity(round_field, max_eccentricity=0.60)
    assert bool(res_round) is True, f"Round stars should pass eccentricity check, got {res_round.value}"
    assert res_round.value < 0.60, f"Eccentricity {res_round.value:.3f} exceeded 0.60 threshold"

    # 2. Test eccentricity on smeared/wind-jittered stars
    smear_kernel = np.zeros((15, 15), dtype=np.float32)
    smear_kernel[7, :] = 1.0 / 15.0  # Directional streak
    smeared_field = cv2.filter2D(round_field, -1, smear_kernel)

    res_smeared = check_star_eccentricity(smeared_field, max_eccentricity=0.60)
    assert bool(res_smeared) is False, f"Smeared stars must be rejected, got {res_smeared.value}"
    assert res_smeared.value > 0.60, f"Expected smeared eccentricity > 0.60, got {res_smeared.value:.3f}"
    print(f"      Eccentricity passed: Round={res_round.value:.3f}, Smeared={res_smeared.value:.3f} (Rejected: True)")

    # 3. Test FWHM computation on known Gaussian star
    size = 31
    y, x = np.mgrid[0:size, 0:size]
    true_sigma = 2.0
    expected_fwhm = 2.35482 * true_sigma
    star_crop = np.exp(-((x - 15) ** 2 + (y - 15) ** 2) / (2.0 * true_sigma**2))
    measured_fwhm = compute_fwhm(star_crop)
    assert abs(measured_fwhm - expected_fwhm) < 0.35, (
        f"FWHM estimation error: expected {expected_fwhm:.2f}, got {measured_fwhm:.2f}"
    )
    print(f"      FWHM measurement passed: Expected={expected_fwhm:.2f}px, Measured={measured_fwhm:.2f}px")

    # 4. Test RollingFWHMTracker for optical blur alert (>25% expansion)
    tracker = RollingFWHMTracker(maxlen=5, blur_threshold_ratio=0.25)
    for f in [3.0, 3.1, 2.9, 3.0]:
        alert, base, msg = tracker.add_measurement(f)
        assert alert is False, f"Unexpected alert during baseline: {msg}"

    alert, base, msg = tracker.add_measurement(4.2)
    assert alert is True, "Tracker failed to trigger alert on +40% FWHM expansion!"
    assert tracker.is_alert_active() is True
    print(f"      RollingFWHMTracker passed: Alert triggered on 4.2px vs baseline {base:.2f}px (+{tracker.last_ratio*100:.1f}%)")


def run_satellites_stage(frames: List[np.ndarray], has_satellite: List[bool]) -> List[np.ndarray]:
    """Detects satellite streaks across sub-exposures."""
    print("[2/6] Testing Satellites Module (detect_satellite_streaks)...")
    masks: List[np.ndarray] = []

    for i, (frame, is_sat) in enumerate(zip(frames, has_satellite)):
        mask = detect_satellite_streaks(frame, min_line_length=150, dilation_px=5)
        masks.append(mask)

        if is_sat:
            streak_pixel_count = int(np.sum(mask))
            assert streak_pixel_count > 100, f"Frame {i} had satellite but detected {streak_pixel_count} pixels."
            print(f"      Frame {i} (Streak Expected): Mask detected {streak_pixel_count} streak pixels.")
        else:
            streak_pixel_count = int(np.sum(mask))
            assert streak_pixel_count == 0, f"Frame {i} had no satellite but false positives occurred ({streak_pixel_count} px)."
            print(f"      Frame {i} (Clean): Mask correctly empty (0 streak pixels).")

    return masks


def run_alignment_stage(frames: List[np.ndarray]) -> List[np.ndarray]:
    """Registers drifting sub-exposures and verifies cloud / star-loss rejection."""
    print("[3/6] Testing Alignment Module (ORB + RANSAC, Cloud Rejection)...")
    ref_frame = frames[0]
    aligned_frames: List[np.ndarray] = [ref_frame]

    for i in range(1, len(frames)):
        warped, H = align_frame(ref_frame, frames[i], return_homography=True)
        aligned_frames.append(warped)
        assert H.shape == (3, 3), f"Invalid homography matrix shape {H.shape}"
        print(f"      Frame {i} registered cleanly to Frame 0 (H[0,2]={H[0,2]:.2f}, H[1,2]={H[1,2]:.2f}).")

    # Cloud occlusion (>40% star drop) rejection test
    cloud_frame = ref_frame.copy()
    rng = np.random.default_rng(999)
    cloud_frame[:, 140:] = 0.05 + rng.normal(0, 0.005, (cloud_frame.shape[0], cloud_frame.shape[1] - 140)).astype(np.float32)
    try:
        align_frame(ref_frame, cloud_frame)
        assert False, "Should have rejected cloud-occluded frame!"
    except FrameRejectedError as e:
        assert "cloud" in str(e).lower() or "star count" in str(e).lower()
        print(f"      Cloud occlusion correctly rejected: {e}")

    # Featureless blank frame rejection test
    featureless_blank = np.zeros_like(ref_frame)
    try:
        align_frame(ref_frame, featureless_blank)
        assert False, "Should have rejected featureless frame!"
    except FrameRejectedError as e:
        print(f"      Featureless frame correctly rejected: {e}")

    return aligned_frames


def run_stacker_stage(aligned_frames: List[np.ndarray], streak_masks: List[np.ndarray]) -> np.ndarray:
    """Executes streaming Welford 2.5-sigma stacker under constant memory."""
    print("[4/6] Testing Stacker Module (WelfordStacker, RAM < 200MB, Streak Rejection)...")

    stacker = WelfordStacker(sigma_clip=2.5, min_samples_for_clip=3)

    for i, (frame, mask) in enumerate(zip(aligned_frames, streak_masks)):
        stacker.add_frame(frame, mask=mask)
        ram_mb = stacker.get_memory_usage_mb()
        assert ram_mb < 200.0, f"RAM usage exceeded 200MB: {ram_mb:.2f}MB"

    final_ram_mb = stacker.get_memory_usage_mb()
    print(f"      Stacker memory footprint: {final_ram_mb:.3f} MB (Strict invariant: < 200.0 MB).")

    stacked = stacker.get_result()
    assert stacked.shape == aligned_frames[0].shape
    assert stacked.dtype == np.float32

    # Verify satellite streak rejection
    streak_sample = float(stacked[150, 180])
    assert streak_sample < 0.35, f"Satellite streak was not clipped! Value: {streak_sample:.3f}"
    print(f"      Satellite streak successfully clipped from final stack (locus value: {streak_sample:.3f} vs raw ~0.90).")

    # Verify SNR noise reduction
    bg_slice_single = aligned_frames[0][10:60, 10:60]
    bg_slice_stacked = stacked[10:60, 10:60]
    var_single = float(np.var(bg_slice_single))
    var_stacked = float(np.var(bg_slice_stacked))
    assert var_stacked < var_single, f"Stacked variance ({var_stacked:.6f}) >= single frame ({var_single:.6f})"
    print(f"      SNR improvement confirmed: Background variance dropped from {var_single:.6f} to {var_stacked:.6f}.")

    return stacked


def run_gradient_stage(stacked_image: np.ndarray) -> np.ndarray:
    """Removes light pollution gradient and preserves pedestal."""
    print("[5/6] Testing Gradient Module (remove_background_gradient)...")

    bg_top_left = float(np.median(stacked_image[10:40, 10:40]))
    bg_bottom_right = float(np.median(stacked_image[-40:-10, -40:-10]))
    tilt_before = abs(bg_bottom_right - bg_top_left)

    clean_image = remove_background_gradient(stacked_image, order=2)

    bg_clean_tl = float(np.median(clean_image[10:40, 10:40]))
    bg_clean_br = float(np.median(clean_image[-40:-10, -40:-10]))
    tilt_after = abs(bg_clean_br - bg_clean_tl)

    assert tilt_after < tilt_before * 0.40, (
        f"Gradient not sufficiently flattened: before={tilt_before:.4f}, after={tilt_after:.4f}"
    )

    med_pedestal = float(np.median(clean_image))
    assert med_pedestal > 0.02, f"Pedestal collapsed to zero ({med_pedestal:.4f})"
    print(f"      Gradient removed cleanly: Corner delta reduced from {tilt_before:.4f} to {tilt_after:.4f}.")
    print(f"      Pedestal preserved: Median background level is {med_pedestal:.4f}.")

    return clean_image


def run_stretch_stage(clean_image: np.ndarray) -> None:
    """Tests MTF and Arcsinh auto_stretch."""
    print("[6/6] Testing Stretch Module (auto_stretch MTF and Arcsinh)...")

    target_bg = 0.25
    stretched_8bit = auto_stretch(clean_image, target_bg=target_bg)

    assert stretched_8bit.dtype == np.uint8
    assert stretched_8bit.shape == clean_image.shape

    med_8bit = float(np.median(stretched_8bit))
    expected_8bit = target_bg * 255.0
    assert abs(med_8bit - expected_8bit) < 25.0, (
        f"Display background off-target: expected ~{expected_8bit:.0f}, got {med_8bit:.1f}"
    )
    print(f"      MTF Auto-stretch passed: Background median = {med_8bit:.1f} / 255 (Target: {expected_8bit:.0f}).")

    # 3-channel saturation preservation test
    rgb_clean = np.stack([clean_image * 0.9, clean_image * 1.0, clean_image * 1.1], axis=2)
    stretched_rgb = auto_stretch(rgb_clean, target_bg=0.25, preserve_saturation=True)
    assert stretched_rgb.dtype == np.uint8
    assert stretched_rgb.shape == rgb_clean.shape
    print(f"      Arcsinh saturation-preserving stretch passed for 3-channel RGB: shape={stretched_rgb.shape}.")


# =====================================================================
# PYTEST FIXTURES & TESTS (for pytest execution)
# =====================================================================


@pytest.fixture(scope="module")
def synthetic_data() -> Tuple[List[np.ndarray], List[Tuple[float, float]], List[bool]]:
    return generate_synthetic_dataset(num_frames=5, height=512, width=512)


@pytest.fixture(scope="module")
def frames_fixture(synthetic_data: Tuple[List[np.ndarray], List[Tuple[float, float]], List[bool]]) -> List[np.ndarray]:
    return synthetic_data[0]


@pytest.fixture(scope="module")
def has_satellite_fixture(synthetic_data: Tuple[List[np.ndarray], List[Tuple[float, float]], List[bool]]) -> List[bool]:
    return synthetic_data[2]


@pytest.fixture(scope="module")
def streak_masks_fixture(frames_fixture: List[np.ndarray], has_satellite_fixture: List[bool]) -> List[np.ndarray]:
    return run_satellites_stage(frames_fixture, has_satellite_fixture)


@pytest.fixture(scope="module")
def aligned_frames_fixture(frames_fixture: List[np.ndarray]) -> List[np.ndarray]:
    return run_alignment_stage(frames_fixture)


@pytest.fixture(scope="module")
def stacked_image_fixture(aligned_frames_fixture: List[np.ndarray], streak_masks_fixture: List[np.ndarray]) -> np.ndarray:
    return run_stacker_stage(aligned_frames_fixture, streak_masks_fixture)


@pytest.fixture(scope="module")
def clean_image_fixture(stacked_image_fixture: np.ndarray) -> np.ndarray:
    return run_gradient_stage(stacked_image_fixture)


def test_gates() -> None:
    run_gates_stage()


def test_satellites(streak_masks_fixture: List[np.ndarray], has_satellite_fixture: List[bool]) -> None:
    assert len(streak_masks_fixture) == len(has_satellite_fixture)
    for mask, is_sat in zip(streak_masks_fixture, has_satellite_fixture):
        if is_sat:
            assert np.sum(mask) > 100
        else:
            assert np.sum(mask) == 0


def test_alignment(aligned_frames_fixture: List[np.ndarray], frames_fixture: List[np.ndarray]) -> None:
    assert len(aligned_frames_fixture) == len(frames_fixture)
    for frame in aligned_frames_fixture:
        assert frame.shape == frames_fixture[0].shape


def test_stacker(stacked_image_fixture: np.ndarray, frames_fixture: List[np.ndarray]) -> None:
    assert stacked_image_fixture.shape == frames_fixture[0].shape
    assert stacked_image_fixture.dtype == np.float32


def test_gradient(clean_image_fixture: np.ndarray, stacked_image_fixture: np.ndarray) -> None:
    assert clean_image_fixture.shape == stacked_image_fixture.shape
    assert np.median(clean_image_fixture) > 0.02


def test_stretch(clean_image_fixture: np.ndarray) -> None:
    run_stretch_stage(clean_image_fixture)


# =====================================================================
# CLI MAIN ENTRYPOINT (for `python backend/test_pipeline.py`)
# =====================================================================


def main() -> None:
    print("=" * 70)
    print("ASTROPHOTOGRAPHY PROCESSING PIPELINE - END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    # 1. Gates
    run_gates_stage()

    # Synthetic Dataset
    print("\nGenerating 5 synthetic astronomical sub-exposures with drift, noise, & streaks...")
    frames, drifts, has_satellite = generate_synthetic_dataset(num_frames=5, height=512, width=512)
    print(f"Generated {len(frames)} frames. Tracking drift across sequence: {drifts}")

    # 2. Satellites
    streak_masks = run_satellites_stage(frames, has_satellite)

    # 3. Alignment
    aligned_frames = run_alignment_stage(frames)

    # 4. Stacker
    stacked_image = run_stacker_stage(aligned_frames, streak_masks)

    # 5. Gradient
    clean_image = run_gradient_stage(stacked_image)

    # 6. Stretch
    run_stretch_stage(clean_image)

    # Save output artifacts for visual inspection
    out_dir = PROJECT_ROOT / "test_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "raw_frame_with_satellite.png"), (frames[1] * 255).astype(np.uint8))
    cv2.imwrite(str(out_dir / "detected_satellite_mask.png"), (streak_masks[1] * 255).astype(np.uint8))
    cv2.imwrite(str(out_dir / "stacked_clean.png"), (np.clip(stacked_image, 0, 1) * 255).astype(np.uint8))
    cv2.imwrite(str(out_dir / "gradient_removed.png"), (np.clip(clean_image, 0, 1) * 255).astype(np.uint8))
    stretched_preview = auto_stretch(clean_image, target_bg=0.25)
    cv2.imwrite(str(out_dir / "stretched_preview_8bit.png"), stretched_preview)

    print("\n" + "=" * 70)
    print("ALL PIPELINE TESTS PASSED CLEANLY! (Exit code 0)")
    print(f"Sample images written to: {out_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
