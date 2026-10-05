"""Comprehensive integration and unit test suite for the Astrolink server, ingest, and intervalometer.

Validates:
1. Captive Portal Bypass (HTTP 204 for iOS, Android, Google, Windows).
2. Universal file ingestion (FITS, TIFF, JPEG, PNG, WebP) via load_universal_frame:
   - Identical output format: 3-channel (H, W, 3) np.float32 [0.0, 1.0].
   - Vertical flip (np.flipud) on FITS files.
3. CameraIntervalometer USB sequencing:
   - Connection lifecycle.
   - Mandatory minimum 2s cooldown delay enforcement.
   - Shutter execution and in-memory frame routing to stacker.
   - Sequence abort / stop_sequence.
4. WebSocket commands:
   - START_SEQUENCE, STOP_SEQUENCE, RESET_STACK.
   - Real-time telemetry broadcast.
5. POST /api/upload parsing incoming frames through load_universal_frame.
6. GET /api/export producing uncompressed 16-bit TIFF files.
7. GPhotoTetherDaemon USB tethering background worker.
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.hardware.intervalometer import CameraIntervalometer
from backend.app.hardware.tether import CapturedFrame, GPhotoTetherDaemon
from backend.app.main import app, intervalometer, session, ws_manager
from backend.app.pipeline.ingest import load_universal_frame


def create_synthetic_frame_bytes(
    width: int = 512,
    height: int = 512,
    num_stars: int = 60,
    seed: int = 42,
    shift: Tuple[float, float] = (0.0, 0.0),
    format_: str = "jpg",
) -> bytes:
    """Generates synthetic starry frame encoded as byte buffer with realistic tracking drift."""
    rng = np.random.default_rng(seed)
    field = np.zeros((height, width), dtype=np.float32)

    x_coords = rng.uniform(50, width - 50, num_stars)
    y_coords = rng.uniform(50, height - 50, num_stars)
    intensities = rng.uniform(0.5, 1.0, num_stars)
    sigmas = rng.uniform(1.4, 2.2, num_stars)

    y_grid, x_grid = np.mgrid[0:height, 0:width]

    for x0, y0, intensity, sigma in zip(x_coords, y_coords, intensities, sigmas):
        r2 = (x_grid - x0) ** 2 + (y_grid - y0) ** 2
        field += (intensity * np.exp(-r2 / (2.0 * sigma**2))).astype(np.float32)

    # Apply mount tracking drift if specified
    dx, dy = shift
    if abs(dx) > 1e-4 or abs(dy) > 1e-4:
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        field = cv2.warpAffine(field, M, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    field = np.clip(field + 0.05 + rng.normal(0, 0.005, (height, width)), 0.0, 1.0)

    if format_.lower() in ("fits", "fit"):
        from astropy.io import fits

        # Create FITS with optical orientation (y=0 at bottom before vertical flip)
        hdu = fits.PrimaryHDU((field * 65535.0).astype(np.uint16))
        buf = io.BytesIO()
        hdu.writeto(buf)
        return buf.getvalue()

    if format_.lower() in ("tif", "tiff"):
        import tifffile

        buf = io.BytesIO()
        tifffile.imwrite(buf, (field * 65535.0).astype(np.uint16), compression=None)
        return buf.getvalue()

    u8 = (field * 255.0).astype(np.uint8)
    if format_.lower() == "png":
        ok, encoded = cv2.imencode(".png", u8)
        assert ok
        return encoded.tobytes()

    if format_.lower() == "webp":
        ok, encoded = cv2.imencode(".webp", u8)
        assert ok
        return encoded.tobytes()

    ok, encoded = cv2.imencode(".jpg", u8, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok, "Failed to encode synthetic JPEG frame"
    return encoded.tobytes()


@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


# =====================================================================
# 1. UNIVERSAL INGESTION TESTS (load_universal_frame)
# =====================================================================


def test_load_universal_frame_fits() -> None:
    """Verifies FITS loading, vertical flip (np.flipud), and 3-channel float32 [0, 1] normalization."""
    from astropy.io import fits

    # Create asymmetric 2D array to verify vertical flip
    arr = np.zeros((100, 100), dtype=np.float32)
    # Bright spot in the top 10 rows (values in uint16 range)
    arr[5:15, 45:55] = 65535.0

    hdu = fits.PrimaryHDU(arr)
    buf = io.BytesIO()
    hdu.writeto(buf)
    fits_bytes = buf.getvalue()

    result = load_universal_frame(fits_bytes)

    # Must return (H, W, 3) float32 [0.0, 1.0]
    assert result.shape == (100, 100, 3), f"Expected (100, 100, 3), got {result.shape}"
    assert result.dtype == np.float32, f"Expected float32, got {result.dtype}"
    assert 0.0 <= result.min() and result.max() <= 1.0

    # In FITS, y=0 is at bottom. load_universal_frame flips it vertically via np.flipud
    # So top 10 rows (5:15) should now be in the bottom 10 rows (85:95)
    bottom_slice = result[85:95, 45:55, :]
    assert bottom_slice.max() > 0.5, "Vertical flip was not correctly applied to FITS image"
    assert result[5:15, 45:55, :].max() < 0.1


def test_load_universal_frame_tiff() -> None:
    """Verifies 16-bit and 8-bit TIFF decoding via tifffile into 3-channel float32."""
    import tifffile

    # 16-bit grayscale TIFF
    img_u16 = np.full((120, 160), 32768, dtype=np.uint16)
    buf_u16 = io.BytesIO()
    tifffile.imwrite(buf_u16, img_u16, compression=None)

    res_16 = load_universal_frame(buf_u16.getvalue())
    assert res_16.shape == (120, 160, 3)
    assert res_16.dtype == np.float32
    assert abs(float(np.median(res_16)) - 0.5) < 0.01

    # 8-bit RGB TIFF
    img_u8_rgb = np.zeros((80, 80, 3), dtype=np.uint8)
    img_u8_rgb[:, :, 0] = 255  # Red channel
    buf_rgb = io.BytesIO()
    tifffile.imwrite(buf_rgb, img_u8_rgb, compression=None)

    res_rgb = load_universal_frame(buf_rgb.getvalue())
    assert res_rgb.shape == (80, 80, 3)
    assert res_rgb.dtype == np.float32
    assert abs(float(res_rgb[10, 10, 0]) - 1.0) < 0.01
    assert float(res_rgb[10, 10, 1]) == 0.0


def test_load_universal_frame_standard_images() -> None:
    """Verifies JPEG, PNG, and WebP decoding into standard 3-channel RGB float32 [0.0, 1.0]."""
    for fmt in ("jpg", "png", "webp"):
        data = create_synthetic_frame_bytes(width=200, height=200, format_=fmt)
        res = load_universal_frame(data)

        assert res.shape == (200, 200, 3), f"Failed shape for {fmt}: {res.shape}"
        assert res.dtype == np.float32, f"Failed dtype for {fmt}: {res.dtype}"
        assert 0.0 <= res.min() and res.max() <= 1.0


# =====================================================================
# 2. CAPTIVE PORTAL BYPASS TESTS
# =====================================================================


def test_captive_portal_bypass(client: TestClient) -> None:
    """Verifies all captive portal bypass endpoints return HTTP 204 No Content."""
    endpoints = [
        "/hotspot-detect.html",  # Apple iOS / macOS
        "/canonical.html",       # Android captive portal probe
        "/generate_204",         # Google connectivity check
        "/ncsi.txt",             # Windows NCSI probe
    ]

    for path in endpoints:
        resp_get = client.get(path)
        assert resp_get.status_code == 204, f"GET {path} returned {resp_get.status_code}, expected 204"
        assert resp_get.content == b"", f"GET {path} should have empty body"

        resp_head = client.head(path)
        assert resp_head.status_code == 204, f"HEAD {path} returned {resp_head.status_code}, expected 204"


# =====================================================================
# 3. CAMERA INTERVALOMETER TESTS
# =====================================================================


def test_camera_intervalometer_lifecycle() -> None:
    """Verifies CameraIntervalometer connection, sequence start, delay enforcement, and stop."""
    captured: List[Tuple[str, float]] = []

    def on_frame(data: bytes, filename: str, exposure: float) -> None:
        captured.append((filename, exposure))

    interv = CameraIntervalometer(on_frame_captured=on_frame, simulate=True)

    # 1. Connect
    assert interv.connect() is True
    assert interv.is_connected is True
    assert interv.is_running is False

    # 2. Start sequence of 2 frames with delay_seconds=2.0 (mandatory minimum)
    start_time = time.time()
    started = interv.start_sequence(exposure_seconds=0.1, frame_count=2, delay_seconds=2.0)
    assert started is True
    assert interv.is_running is True

    # Wait for sequence to complete
    max_wait = 6.0
    while interv.is_running and (time.time() - start_time) < max_wait:
        time.sleep(0.1)

    elapsed = time.time() - start_time
    assert len(captured) == 2, f"Expected 2 frames captured, got {len(captured)}"
    # Mandatory cooldown delay of 2.0s means elapsed time should be >= 2.0s
    assert elapsed >= 2.0, f"Sequence finished too fast ({elapsed:.2f}s); cooldown delay was not enforced"
    assert interv.is_running is False

    # 3. Test stop_sequence
    interv.start_sequence(exposure_seconds=1.0, frame_count=10, delay_seconds=2.0)
    assert interv.is_running is True
    time.sleep(0.2)
    interv.stop_sequence()
    assert interv.is_running is False
    interv.disconnect()


# =====================================================================
# 4. WEBSOCKET COMMANDS & REAL-TIME BROADCAST TESTS
# =====================================================================


def _receive_websocket_msg(ws, expected_type: str, max_attempts: int = 15) -> dict:
    """Helper to drain async events (both binary previews and JSON) and locate expected JSON message."""
    import json

    for _ in range(max_attempts):
        raw = ws.receive()
        if "text" in raw:
            try:
                msg = json.loads(raw["text"])
                if msg.get("type") == expected_type:
                    return msg
            except Exception:
                pass
        # Ignore binary frames (e.g. WebP preview bytes)
    raise TimeoutError(f"Did not receive message of type {expected_type}")


def test_websocket_commands(client: TestClient) -> None:
    """Verifies WebSocket command routing: START_SEQUENCE, STOP_SEQUENCE, RESET_STACK."""
    session.reset()

    with client.websocket_connect("/ws") as ws:
        # Initial greeting payload
        init_msg = _receive_websocket_msg(ws, "telemetry")
        assert init_msg["type"] == "telemetry"

        # Command 1: START_SEQUENCE
        ws.send_json({
            "command": "START_SEQUENCE",
            "exposure_seconds": 0.1,
            "frame_count": 2,
            "delay_seconds": 2.0,
        })
        resp_start = _receive_websocket_msg(ws, "command_response")
        assert resp_start["command"] == "START_SEQUENCE"
        assert resp_start["success"] is True

        # Wait briefly for intervalometer
        time.sleep(0.1)

        # Command 2: STOP_SEQUENCE
        ws.send_json({"command": "STOP_SEQUENCE"})
        resp_stop = _receive_websocket_msg(ws, "command_response")
        assert resp_stop["command"] == "STOP_SEQUENCE"
        assert resp_stop["success"] is True

        # Command 3: RESET_STACK
        ws.send_json({"command": "RESET_STACK"})
        resp_reset = _receive_websocket_msg(ws, "command_response")
        assert resp_reset["command"] == "RESET_STACK"
        assert resp_reset["success"] is True
        assert session.stacker.total_frames_processed == 0


# =====================================================================
# 5. API UPLOAD & EXPORT INTEGRATION TESTS
# =====================================================================


def test_upload_universal_formats(client: TestClient) -> None:
    """Verifies POST /api/upload accepts FITS, TIFF, and JPEG through universal ingestion."""
    session.reset()

    # Upload FITS frame 1 (becomes reference frame)
    fits_bytes_1 = create_synthetic_frame_bytes(seed=10, shift=(0.0, 0.0), format_="fits")
    resp_fits_1 = client.post("/api/upload", files={"file": ("target_01.fits", fits_bytes_1, "application/octet-stream")})
    assert resp_fits_1.status_code == 200, resp_fits_1.text
    assert resp_fits_1.json()["telemetry"]["stackCount"] == 1

    # Upload FITS frame 2 (consecutive sub-exposure with tracking drift)
    fits_bytes_2 = create_synthetic_frame_bytes(seed=10, shift=(3.5, -2.0), format_="fits")
    resp_fits_2 = client.post("/api/upload", files={"file": ("target_02.fits", fits_bytes_2, "application/octet-stream")})
    assert resp_fits_2.status_code == 200, resp_fits_2.text
    data2 = resp_fits_2.json()
    assert data2["telemetry"]["stackCount"] == 2
    assert data2["telemetry"]["snrGain"] == 1.41

    # Reset and test consecutive TIFF sub-exposures
    session.reset()
    tiff_bytes_1 = create_synthetic_frame_bytes(seed=20, shift=(0.0, 0.0), format_="tiff")
    resp_tiff_1 = client.post("/api/upload", files={"file": ("target_01.tiff", tiff_bytes_1, "image/tiff")})
    assert resp_tiff_1.status_code == 200, resp_tiff_1.text
    assert resp_tiff_1.json()["telemetry"]["stackCount"] == 1

    tiff_bytes_2 = create_synthetic_frame_bytes(seed=20, shift=(3.0, -1.5), format_="tiff")
    resp_tiff_2 = client.post("/api/upload", files={"file": ("target_02.tiff", tiff_bytes_2, "image/tiff")})
    assert resp_tiff_2.status_code == 200, resp_tiff_2.text
    assert resp_tiff_2.json()["telemetry"]["stackCount"] == 2

    # Upload JPEG sub-exposure
    jpg_bytes = create_synthetic_frame_bytes(seed=20, shift=(6.0, -3.0), format_="jpg")
    resp_jpg = client.post("/api/upload", files={"file": ("target_03.jpg", jpg_bytes, "image/jpeg")})
    assert resp_jpg.status_code == 200, resp_jpg.text
    assert resp_jpg.json()["telemetry"]["stackCount"] == 3


def test_export_16bit_tiff_after_stack(client: TestClient) -> None:
    """Verifies GET /api/export produces an uncompressed 16-bit TIFF with valid headers."""
    import tifffile

    assert session.stacker.total_frames_processed > 0

    resp = client.get("/api/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/tiff"
    assert "attachment; filename=master_stack_16bit.tiff" in resp.headers["content-disposition"]

    with io.BytesIO(resp.content) as buf:
        tiff_img = tifffile.imread(buf)

    assert tiff_img.dtype == np.uint16
    assert tiff_img.shape[:2] == (512, 512)
    assert tiff_img.max() > 0


def test_hardware_tether_daemon() -> None:
    """Verifies GPhotoTetherDaemon USB tethering background worker."""
    received: List[CapturedFrame] = []

    daemon = GPhotoTetherDaemon(on_frame_callback=lambda f: received.append(f), simulate=True)
    daemon.start()
    assert daemon.is_running is True

    sample_data = create_synthetic_frame_bytes(seed=999)
    daemon.inject_simulated_frame("usb_shutter.jpg", sample_data)

    assert len(daemon.ingest_queue.get(timeout=1.0).data) == len(sample_data)
    assert len(received) == 1
    assert received[0].filename == "usb_shutter.jpg"

    daemon.stop()
    assert daemon.is_running is False


def test_feedback_attachment_path_traversal_prevention(client: TestClient) -> None:
    """Verifies that path traversal attempts in feedback attachments are safely rejected."""
    from backend.app.feedback import feedback_manager

    traversal_paths = [
        "..",
        ".",
        "../feedback.json",
        "../../etc/passwd",
        "/etc/passwd",
        "nested/../../secret.txt",
    ]

    # Direct manager validation
    for path_str in traversal_paths:
        assert feedback_manager.get_attachment_path(path_str) is None

    # HTTP API validation (testing URL-encoded traversal parameters)
    http_traversal_paths = [
        "..%2Ffeedback.json",
        "..%2F..%2Fetc%2Fpasswd",
        "%2Fetc%2Fpasswd",
        "nested%2F..%2F..%2Fsecret.txt",
    ]
    for filename in http_traversal_paths:
        resp = client.get(f"/api/feedback/attachment/{filename}")
        assert resp.status_code == 404, f"Expected 404 for traversal path '{filename}', got {resp.status_code}"


def test_feedback_attachment_valid_serving(client: TestClient) -> None:
    """Verifies that valid feedback attachments within attachments_dir are served correctly."""
    from backend.app.feedback import feedback_manager

    # Create a legitimate test attachment in attachments_dir
    test_filename = "test_ss_1.png"
    target_path = feedback_manager.attachments_dir / test_filename
    target_path.write_bytes(b"PNG_DUMMY_DATA")

    try:
        resp = client.get(f"/api/feedback/attachment/{test_filename}")
        assert resp.status_code == 200
        assert resp.content == b"PNG_DUMMY_DATA"
    finally:
        if target_path.exists():
            target_path.unlink()
