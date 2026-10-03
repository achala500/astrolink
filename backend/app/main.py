"""FastAPI server application for wireless astrophotography field operations.

Features:
1. Captive Portal Bypass (HTTP 204 for iOS, Android, Google, Windows).
2. Network Transport & Hardware Control:
   - Universal file ingestion (FITS, RAW, Linear DNG, TIFF, JPEG, PNG, WebP) via load_universal_frame.
   - Hardware camera intervalometer sequencing via CameraIntervalometer.
   - POST /api/upload: Multipart frame ingestion into RAM, WelfordStacker, and WebSocket broadcast.
   - GET /api/export: Uncompressed 16-bit TIFF export using tifffile.
   - WebSocket /ws: Interactive command handling (START_SEQUENCE, STOP_SEQUENCE, RESET_STACK)
     and real-time telemetry / 1080p WebP preview streaming.
3. Zero-Config mDNS: Broadcasts `_http._tcp.local.` as `astrolink.local` on port 8080.
4. Hardware Tethering: USB camera ingestion daemon integration.
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import io
import json
import logging
import math
import os
import re
import shutil
import socket
import sys
import threading
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Ensure backend package can be resolved
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.hardware.detector import camera_detector
from backend.app.hardware.intervalometer import CameraIntervalometer
from backend.app.hardware.tether import CapturedFrame, GPhotoTetherDaemon
from backend.app.licensing import license_manager, verify_license_key
from backend.app.feedback import feedback_manager
from backend.app.pipeline.alignment import FrameRejectedError, align_frame
from backend.app.pipeline.gates import (
    RollingFWHMTracker,
    check_star_eccentricity,
    compute_fwhm,
)
from backend.app.pipeline.gradient import remove_background_gradient
from backend.app.pipeline.ingest import _normalize_array_to_float32, load_universal_frame
from backend.app.pipeline.satellites import detect_satellite_streaks
from backend.app.pipeline.stacker import WelfordStacker
from backend.app.pipeline.stretch import auto_stretch

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("astrolink.server")
APP_VERSION = "0.1.4"
UPDATE_REPOSITORY = "achala500/astrolink"
MAX_UPLOAD_BYTES = 128 * 1024 * 1024  # protect the field station from accidental huge uploads

def _extract_bearer_token(request: Request) -> str:
    supplied = request.headers.get("authorization", "")
    if supplied.lower().startswith("bearer "):
        return supplied[7:].strip()
    return ""


def _require_api_token(request: Request) -> None:
    """Protect state-changing/data endpoints when API auth is configured."""
    expected = os.environ.get("ASTROLINK_API_TOKEN", "").strip()
    if expected and not hmac.compare_digest(_extract_bearer_token(request), expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API authentication required")


def _require_ws_token(websocket: WebSocket) -> None:
    expected = os.environ.get("ASTROLINK_API_TOKEN", "").strip()
    if not expected:
        return
    supplied = websocket.query_params.get("token", "")
    auth = websocket.headers.get("authorization", "")
    if not supplied and auth.lower().startswith("bearer "):
        supplied = auth[7:].strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise RuntimeError("WebSocket authentication required")


def _require_admin_token(request: Request) -> None:
    """Protect management/feedback endpoints when deployed publicly.

    Local installations remain frictionless when no token is configured. Cloud
    operators should set ASTROLINK_ADMIN_TOKEN and send it as a Bearer token.
    """
    expected = os.environ.get("ASTROLINK_ADMIN_TOKEN", "").strip()
    if not expected:
        return
    supplied = _extract_bearer_token(request)
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrator authentication required")


# =====================================================================
# WEBSOCKET CONNECTION MANAGER
# =====================================================================


class ConnectionManager:
    """Manages active WebSocket client connections for real-time field telemetry."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Total clients: %d", len(self.active_connections))

    async def broadcast_json(self, data: Dict[str, Any]) -> None:
        """Broadcasts a JSON message to all active WebSocket clients."""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.debug("Failed to send WebSocket JSON: %s", e)
                self.disconnect(connection)

    async def broadcast_bytes(self, data: bytes) -> None:
        """Broadcasts binary data (e.g. WebP preview bytes) to all clients."""
        for connection in list(self.active_connections):
            try:
                await connection.send_bytes(data)
            except Exception as e:
                logger.debug("Failed to send WebSocket binary: %s", e)
                self.disconnect(connection)


ws_manager = ConnectionManager()


# =====================================================================
# ASTROPHOTOGRAPHY SESSION STATE & ENGINE
# =====================================================================


class AstrophotographySession:
    """Encapsulates active field stacking session, quality gates, and telemetry."""

    def __init__(self) -> None:
        self.stacker = WelfordStacker(sigma_clip=2.5, min_samples_for_clip=3)
        self.fwhm_tracker = RollingFWHMTracker(maxlen=5, blur_threshold_ratio=0.25)
        self.ref_frame: Optional[np.ndarray] = None
        self.total_exp_seconds: float = 0.0
        self.last_fwhm: float = 0.0
        self.last_alert_message: Optional[str] = None
        self.last_preview_webp_b64: Optional[str] = None
        self.last_preview_webp_bytes: Optional[bytes] = None
        self.last_frame_name: Optional[str] = None
        self.reveal_deep_sky = True
        self.clear_city_glow = True
        # Uploads and camera callbacks can arrive on different threads. The
        # stacker is stateful, so serialize a complete frame transaction.
        self._lock = threading.RLock()
        configured_session = os.environ.get("ASTROLINK_SESSION_FILE", "").strip()
        self._session_file = Path(configured_session).expanduser() if configured_session else None
        self._load_persisted_session()

    def _load_persisted_session(self) -> None:
        """Restore an optional session snapshot from a mounted persistent volume."""
        if not self._session_file or not self._session_file.is_file():
            return
        try:
            with np.load(self._session_file, allow_pickle=False) as saved:
                shape = tuple(int(x) for x in saved["shape"])
                if len(shape) not in (2, 3) or any(dim <= 0 for dim in shape) or int(np.prod(shape)) > 100_000_000:
                    raise ValueError("persisted frame shape is invalid or too large")
                mean = saved["mean"]
                m2 = saved["m2"]
                counts = saved["counts"]
                if mean.shape != shape or m2.shape != shape or counts.shape != shape:
                    raise ValueError("persisted accumulator shapes do not match")
                self.stacker._init_buffers(shape)
                self.stacker.mean = mean.astype(np.float32)
                self.stacker.m2 = m2.astype(np.float32)
                self.stacker.counts = counts.astype(np.uint32)
                if not np.isfinite(self.stacker.mean).all() or not np.isfinite(self.stacker.m2).all():
                    raise ValueError("persisted accumulator contains non-finite values")
                self.stacker.total_frames_processed = int(saved["total_frames"])
                ref_frame = saved["ref_frame"]
                if ref_frame.shape != shape or not np.isfinite(ref_frame).all():
                    raise ValueError("persisted reference frame is invalid")
                self.ref_frame = ref_frame.astype(np.float32)
                self.total_exp_seconds = float(saved["total_exp_seconds"])
                self.last_fwhm = float(saved["last_fwhm"])
                logger.info("Restored persisted AstroLink session (%d frames)", self.stacker.total_frames_processed)
        except Exception as exc:
            logger.warning("Ignoring invalid persisted session snapshot: %s", exc)

    def _persist_session(self) -> None:
        if not self._session_file or self.stacker.mean is None or self.stacker.m2 is None or self.stacker.counts is None or self.ref_frame is None:
            return
        self._session_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self._session_file.with_suffix(self._session_file.suffix + ".tmp")
        try:
            np.savez_compressed(temp, shape=np.asarray(self.stacker.mean.shape, dtype=np.int64), mean=self.stacker.mean, m2=self.stacker.m2, counts=self.stacker.counts, total_frames=np.asarray(self.stacker.total_frames_processed), ref_frame=self.ref_frame, total_exp_seconds=np.asarray(self.total_exp_seconds), last_fwhm=np.asarray(self.last_fwhm))
            generated = Path(str(temp) + ".npz")
            generated.replace(temp)
            temp.replace(self._session_file)
        except Exception as exc:
            logger.warning("Could not persist session snapshot: %s", exc)
            temp.unlink(missing_ok=True)
            Path(str(temp) + ".npz").unlink(missing_ok=True)

    def set_processing_options(self, reveal_deep_sky: Optional[bool] = None, clear_city_glow: Optional[bool] = None) -> Dict[str, bool]:
        """Updates display processing options for future previews."""
        with self._lock:
            if reveal_deep_sky is not None:
                self.reveal_deep_sky = bool(reveal_deep_sky)
            if clear_city_glow is not None:
                self.clear_city_glow = bool(clear_city_glow)
            return {"revealDeepSky": self.reveal_deep_sky, "clearCityGlow": self.clear_city_glow}

    def reset(self) -> None:
        """Resets the live stacker and telemetry atomically."""
        with self._lock:
            self._reset_unlocked()

    def _reset_unlocked(self) -> None:
        self.stacker.reset()
        self.fwhm_tracker = RollingFWHMTracker(maxlen=5, blur_threshold_ratio=0.25)
        self.ref_frame = None
        self.total_exp_seconds = 0.0
        self.last_fwhm = 0.0
        self.last_alert_message = None
        self.last_preview_webp_b64 = None
        self.last_preview_webp_bytes = None
        self.last_frame_name = None
        if self._session_file:
            self._session_file.unlink(missing_ok=True)

    def process_sub_exposure(
        self,
        image_bytes: Any,
        filename: str = "frame.jpg",
        sub_exp_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """Processes one frame atomically across upload and camera threads."""
        with self._lock:
            return self._process_sub_exposure(image_bytes, filename, sub_exp_seconds)

    def _process_sub_exposure(
        self,
        image_bytes: Any,
        filename: str = "frame.jpg",
        sub_exp_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """Ingests sub-exposure through universal loader, quality gates, alignment, stacking, gradient, and stretch."""
        # 0. Offline Cryptographic License Frame Limit Check
        max_allowed = license_manager.get_max_frames()
        if max_allowed is not None and self.stacker.total_frames_processed >= max_allowed:
            alert_msg = f"TRIAL_LIMIT: Free tier limited to {max_allowed} frames. Activate offline license for unlimited stacking."
            self.last_alert_message = alert_msg
            logger.warning("Frame %s rejected: session reached free tier limit of %d frames.", filename, max_allowed)
            return {
                "accepted": False,
                "reason": "license_limit_reached",
                "details": alert_msg,
                "telemetry": {
                    "stackCount": self.stacker.total_frames_processed,
                    "totalExp": round(self.total_exp_seconds, 1),
                    "fwhm": self.last_fwhm,
                    "snrGain": round(math.sqrt(max(1, self.stacker.total_frames_processed)), 2),
                    "alertMessage": alert_msg,
                },
                "license": license_manager.status.to_dict(),
            }

        # 1. Universal format decoding (FITS, RAW, Linear DNG, TIFF, JPEG, PNG, WebP)
        # Guarantees standard 3-channel (H, W, 3) float32 in range [0.0, 1.0]
        if isinstance(image_bytes, np.ndarray):
            if image_bytes.ndim not in (2, 3):
                raise ValueError(f"Expected a 2D or 3D frame, got shape {image_bytes.shape}")
            frame = _normalize_array_to_float32(image_bytes)
        else:
            frame = load_universal_frame(image_bytes)

        if frame.size == 0 or not np.isfinite(frame).all():
            raise ValueError("Frame contains no usable finite pixel data")

        # Single-channel 2D grayscale for star gates, streak detection, and registration
        if frame.ndim == 3:
            gray = cv2.cvtColor((frame * 255.0).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        else:
            gray = frame

        # 2. Quality Gate: Star Eccentricity
        gate_res = check_star_eccentricity(gray, max_eccentricity=0.60)
        if not gate_res.passed:
            logger.warning("Frame %s rejected by eccentricity gate: %s", filename, gate_res.details)
            return {
                "accepted": False,
                "reason": "eccentricity_rejected",
                "eccentricity": gate_res.value,
                "details": gate_res.details,
            }

        # 3. Quality Gate: Star FWHM & Blur Tracker
        h, w = gray.shape[:2]
        center_crop = gray[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]
        current_fwhm = compute_fwhm(center_crop)
        is_blur, baseline_fwhm, blur_msg = self.fwhm_tracker.add_measurement(current_fwhm)
        self.last_fwhm = round(current_fwhm, 2)
        self.last_alert_message = blur_msg if is_blur else None

        # 4. Satellite Streak Detection
        streak_mask = detect_satellite_streaks(gray, min_line_length=150, dilation_px=5)

        # 5. Star Alignment
        if self.ref_frame is None:
            self.ref_frame = gray.copy()
            aligned_frame = frame
        else:
            try:
                aligned_frame = align_frame(self.ref_frame, frame)
            except FrameRejectedError as e:
                logger.warning("Frame %s rejected by alignment gate: %s", filename, e)
                return {
                    "accepted": False,
                    "reason": "alignment_rejected",
                    "details": str(e),
                }

        # 6. Streaming Welford Stacking
        self.stacker.add_frame(aligned_frame, mask=streak_mask)
        self.total_exp_seconds += sub_exp_seconds
        self.last_frame_name = filename
        self._persist_session()

        # 7. Optional background-gradient removal. The UI controls are now
        # functional rather than merely changing their visual state.
        stacked_raw = self.stacker.get_result()
        clean_stacked = (
            remove_background_gradient(stacked_raw, order=2)
            if self.clear_city_glow else stacked_raw
        )

        # 8. Optional nonlinear display stretch (the exported stack remains linear).
        stretched_preview = (
            auto_stretch(clean_stacked, target_bg=0.25, preserve_saturation=(clean_stacked.ndim == 3))
            if self.reveal_deep_sky else np.clip(clean_stacked * 255.0, 0, 255).astype(np.uint8)
        )

        # 9. Scale to 1080p display preview
        prev_h, prev_w = stretched_preview.shape[:2]
        scale_1080p = min(1.0, 1920.0 / prev_w, 1080.0 / prev_h)
        if scale_1080p < 1.0:
            target_w = int(round(prev_w * scale_1080p))
            target_h = int(round(prev_h * scale_1080p))
            preview_1080p = cv2.resize(stretched_preview, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            preview_1080p = stretched_preview

        # OpenCV expects BGR when encoding color images; the ingestion pipeline
        # uses RGB. Convert here so red/blue channels are not swapped in previews.
        preview_for_encoding = (
            cv2.cvtColor(preview_1080p, cv2.COLOR_RGB2BGR)
            if preview_1080p.ndim == 3 and preview_1080p.shape[2] == 3
            else preview_1080p
        )
        ok, webp_buffer = cv2.imencode(".webp", preview_for_encoding, [cv2.IMWRITE_WEBP_QUALITY, 85])
        if ok:
            self.last_preview_webp_bytes = webp_buffer.tobytes()
            b64_str = base64.b64encode(self.last_preview_webp_bytes).decode("ascii")
            self.last_preview_webp_b64 = f"data:image/webp;base64,{b64_str}"
        else:
            self.last_preview_webp_bytes = None
            self.last_preview_webp_b64 = None

        stack_count = self.stacker.total_frames_processed
        snr_gain = round(math.sqrt(max(1, stack_count)), 2)

        telemetry = {
            "stackCount": stack_count,
            "totalExp": round(self.total_exp_seconds, 1),
            "fwhm": self.last_fwhm,
            "snrGain": snr_gain,
            "alertMessage": self.last_alert_message,
            "revealDeepSky": self.reveal_deep_sky,
            "clearCityGlow": self.clear_city_glow,
        }

        return {
            "accepted": True,
            "telemetry": telemetry,
            "preview": self.last_preview_webp_b64,
            "filename": filename,
        }

    process_frame = process_sub_exposure


session = AstrophotographySession()


# =====================================================================
# CAMERA INTERVALOMETER INTEGRATION
# =====================================================================


def _on_intervalometer_frame_captured(data: bytes, filename: str, exposure_seconds: float) -> None:
    """Callback receiving camera frames from intervalometer, feeding stacker and broadcasting."""
    logger.info("Intervalometer captured frame: %s (%.1fs)", filename, exposure_seconds)
    try:
        result = session.process_sub_exposure(data, filename=filename, sub_exp_seconds=exposure_seconds)
        if result.get("accepted"):
            payload = {
                "type": "telemetry",
                **result["telemetry"],
                "preview": result.get("preview"),
            }
            # Run broadcast on running event loop or schedule threadsafe
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ws_manager.broadcast_json(payload))
                if session.last_preview_webp_bytes:
                    loop.create_task(ws_manager.broadcast_bytes(session.last_preview_webp_bytes))
            except RuntimeError:
                asyncio.run(ws_manager.broadcast_json(payload))
                if session.last_preview_webp_bytes:
                    asyncio.run(ws_manager.broadcast_bytes(session.last_preview_webp_bytes))
    except Exception as err:
        logger.error("Error processing intervalometer frame %s: %s", filename, err, exc_info=True)


intervalometer = CameraIntervalometer(
    on_frame_captured=_on_intervalometer_frame_captured,
    simulate=False,
)


# =====================================================================
# ZERO-CONFIG mDNS & APPLICATION LIFESPAN
# =====================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown hooks, including mDNS broadcast."""
    zeroconf_instance = None
    service_info = None

    # Startup: Broadcast mDNS astrolink.local on port 8080 in background thread
    def _start_mdns():
        nonlocal zeroconf_instance, service_info
        try:
            from zeroconf import IPVersion, ServiceInfo, Zeroconf

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            except Exception:
                local_ip = "127.0.0.1"
            finally:
                s.close()

            zeroconf_instance = Zeroconf(ip_version=IPVersion.V4Only)
            service_info = ServiceInfo(
                type_="_http._tcp.local.",
                name="astrolink._http._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=int(os.environ.get("ASTROLINK_PORT", os.environ.get("PORT", "8080"))),
                server="astrolink.local.",
                properties={"path": "/"},
            )
            zeroconf_instance.register_service(service_info)
            logger.info("Zero-Config mDNS broadcast active: astrolink.local:8080 on %s", local_ip)
        except Exception as e:
            logger.warning("Zero-Config mDNS registration not available or skipped: %s", e)

    if os.environ.get("ASTROLINK_DISABLE_MDNS", "").lower() not in {"1", "true", "yes"}:
        threading.Thread(target=_start_mdns, daemon=True, name="mDNS-Broadcast").start()
    else:
        logger.info("mDNS disabled by ASTROLINK_DISABLE_MDNS")

    # Initialize Hardware Tethering Daemon
    def on_tether_frame(frame: CapturedFrame) -> None:
        logger.info("Hardware tether triggered frame ingestion: %s", frame.filename)
        _on_intervalometer_frame_captured(frame.data, frame.filename, 30.0)

    tether_daemon = GPhotoTetherDaemon(on_frame_callback=on_tether_frame, simulate=True)
    if os.environ.get("ASTROLINK_DISABLE_HARDWARE", "").lower() not in {"1", "true", "yes"}:
        tether_daemon.start()
    else:
        logger.info("Camera tethering disabled by ASTROLINK_DISABLE_HARDWARE")

    yield

    # Shutdown: Teardown intervalometer, tether daemon, and mDNS
    intervalometer.stop_sequence()
    tether_daemon.stop()

    if zeroconf_instance and service_info:
        try:
            zeroconf_instance.unregister_service(service_info)
            zeroconf_instance.close()
            logger.info("Zero-Config mDNS unregistered cleanly.")
        except Exception as e:
            logger.debug("Error during mDNS teardown: %s", e)


app = FastAPI(
    title="Astrolink Smart Field Controller",
    description="Wireless sub-exposure stacking, camera tethering, and live field telemetry.",
    version="2.0.0",
    lifespan=lifespan,
)

# Same-origin is the normal deployment. Explicit origins are supported for a
# separate frontend; wildcard access can be enabled only for local/offline use.
configured_origins = [origin.strip() for origin in os.environ.get("ASTROLINK_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# =====================================================================
# 1. CAPTIVE PORTAL BYPASS (CRITICAL FOR MOBILE HOTSPOT)
# =====================================================================


@app.get("/hotspot-detect.html", status_code=status.HTTP_204_NO_CONTENT)
@app.head("/hotspot-detect.html", status_code=status.HTTP_204_NO_CONTENT)
async def captive_apple():
    """Captive portal bypass route for Apple iOS / macOS devices."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/canonical.html", status_code=status.HTTP_204_NO_CONTENT)
@app.head("/canonical.html", status_code=status.HTTP_204_NO_CONTENT)
async def captive_android():
    """Captive portal bypass route for Android devices."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/generate_204", status_code=status.HTTP_204_NO_CONTENT)
@app.head("/generate_204", status_code=status.HTTP_204_NO_CONTENT)
async def captive_google():
    """Captive portal bypass route for Google connectivity probes."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/ncsi.txt", status_code=status.HTTP_204_NO_CONTENT)
@app.head("/ncsi.txt", status_code=status.HTTP_204_NO_CONTENT)
async def captive_windows():
    """Captive portal bypass route for Windows NCSI probes."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =====================================================================
# 2. NETWORK TRANSPORT API (UPLOAD, EXPORT, WEBSOCKET COMMANDS)
# =====================================================================


@app.post("/api/upload")
async def upload_frame(request: Request, file: UploadFile = File(...)):
    """Ingests multipart sub-exposures through universal decoding into WelfordStacker.

    Supports FITS, DSLR RAWs, Linear DNGs, TIFF, JPEG, PNG, and WebP formats.
    Broadcasts real-time telemetry and 1080p WebP previews across WebSocket clients.
    """
    _require_api_token(request)
    try:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Frame exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB upload limit",
            )
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded frame is empty")

        filename = file.filename or "sub_exposure.jpg"
        result = session.process_sub_exposure(data, filename=filename)

        if not result.get("accepted"):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={
                    "status": "rejected",
                    "reason": result.get("reason"),
                    "details": result.get("details"),
                },
            )

        telemetry = result["telemetry"]
        preview = result["preview"]

        ws_payload = {
            "type": "telemetry",
            **telemetry,
            "preview": preview,
        }
        await ws_manager.broadcast_json(ws_payload)

        if session.last_preview_webp_bytes:
            await ws_manager.broadcast_bytes(session.last_preview_webp_bytes)

        return {
            "status": "success",
            "telemetry": telemetry,
            "preview": preview,
        }

    except HTTPException:
        raise
    except (ValueError, ImportError) as e:
        logger.warning("Rejected frame upload: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e
    except Exception as e:
        logger.error("Failed to ingest frame: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Frame ingestion failed unexpectedly",
        ) from e


@app.get("/api/export")
async def export_master_stack(request: Request):
    """Exports current master stack as an uncompressed 16-bit TIFF using tifffile."""
    _require_api_token(request)
    if session.stacker.mean is None or session.stacker.total_frames_processed == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No astronomical sub-exposures have been stacked yet.",
        )

    try:
        import tifffile

        stacked_clean = session.stacker.get_result()
        img_u16 = np.clip(stacked_clean * 65535.0, 0, 65535).astype(np.uint16)

        buffer = io.BytesIO()
        tifffile.imwrite(buffer, img_u16, compression=None)
        buffer.seek(0)
        tiff_bytes = buffer.getvalue()

        return Response(
            content=tiff_bytes,
            media_type="image/tiff",
            headers={
                "Content-Disposition": "attachment; filename=master_stack_16bit.tiff",
                "X-Stack-Count": str(session.stacker.total_frames_processed),
            },
        )
    except Exception as e:
        logger.error("Exporting TIFF failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate uncompressed 16-bit TIFF: {str(e)}",
        )


@app.websocket("/ws")
async def websocket_telemetry(websocket: WebSocket):
    """Streams real-time telemetry/previews and executes hardware camera control commands."""
    try:
        _require_ws_token(websocket)
    except RuntimeError:
        await websocket.close(code=1008, reason="Authentication required")
        return
    await ws_manager.connect(websocket)

    # Dispatch current telemetry state upon connection
    stack_count = session.stacker.total_frames_processed
    snr_gain = round(math.sqrt(max(1, stack_count)), 2)
    init_payload = {
        "type": "telemetry",
        "stackCount": stack_count,
        "totalExp": round(session.total_exp_seconds, 1),
        "fwhm": session.last_fwhm,
        "snrGain": snr_gain,
        "alertMessage": session.last_alert_message,
        "preview": session.last_preview_webp_b64,
        "intervalometerRunning": intervalometer.is_running,
    }
    await websocket.send_json(init_payload)

    try:
        while True:
            text = await websocket.receive_text()
            cmd_data: Dict[str, Any] = {}
            command = text.strip()

            try:
                cmd_data = json.loads(text)
                if isinstance(cmd_data, dict):
                    command = cmd_data.get("command") or cmd_data.get("action") or command
            except (json.JSONDecodeError, AttributeError):
                # Plain text command payload or invalid JSON
                pass  # nosec B110

            # Handle WebSocket Commands
            if command == "START_SEQUENCE":
                try:
                    exposure_seconds = float(cmd_data.get("exposure_seconds", 30.0))
                    frame_count = int(cmd_data.get("frame_count", 10))
                    delay_seconds = float(cmd_data.get("delay_seconds", 2.0))
                except (TypeError, ValueError):
                    await websocket.send_json({"type": "command_response", "command": "START_SEQUENCE", "success": False, "error": "Exposure, frame count, and delay must be numeric"})
                    continue
                if not (0.1 <= exposure_seconds <= 86400 and 1 <= frame_count <= 10000 and 0 <= delay_seconds <= 86400):
                    await websocket.send_json({"type": "command_response", "command": "START_SEQUENCE", "success": False, "error": "Sequence values are outside supported limits"})
                    continue
                iso = cmd_data.get("iso", None)
                bulb_mode = bool(cmd_data.get("bulb_mode", False))

                started = intervalometer.start_sequence(
                    exposure_seconds=exposure_seconds,
                    frame_count=frame_count,
                    delay_seconds=delay_seconds,
                    iso=iso,
                    bulb_mode=bulb_mode,
                )
                await websocket.send_json({
                    "type": "command_response",
                    "command": "START_SEQUENCE",
                    "success": started,
                    "running": intervalometer.is_running,
                })

            elif command == "STOP_SEQUENCE":
                intervalometer.stop_sequence()
                await websocket.send_json({
                    "type": "command_response",
                    "command": "STOP_SEQUENCE",
                    "success": True,
                    "running": False,
                })

            elif command == "RESET_STACK":
                session.reset()
                reset_payload = {
                    "type": "telemetry",
                    "stackCount": 0,
                    "totalExp": 0.0,
                    "fwhm": 0.0,
                    "snrGain": 1.0,
                    "alertMessage": None,
                    "preview": None,
                    "intervalometerRunning": intervalometer.is_running,
                }
                await ws_manager.broadcast_json(reset_payload)
                await websocket.send_json({
                    "type": "command_response",
                    "command": "RESET_STACK",
                    "success": True,
                })

            elif command == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("WebSocket client error: %s", e)
        ws_manager.disconnect(websocket)


@app.get("/api/status")
async def get_status():
    """Returns general server and stacking state."""
    stack_count = session.stacker.total_frames_processed
    return {
        "status": "online",
        "stackCount": stack_count,
        "totalExp": round(session.total_exp_seconds, 1),
        "fwhm": session.last_fwhm,
        "snrGain": round(math.sqrt(max(1, stack_count)), 2),
        "alertMessage": session.last_alert_message,
        "activeClients": len(ws_manager.active_connections),
        "intervalometerRunning": intervalometer.is_running,
    }


@app.get("/api/settings")
async def get_processing_settings():
    """Returns the active preview-processing settings."""
    return session.set_processing_options()


@app.get("/api/update/check")
async def check_for_updates():
    """Checks GitHub Releases without exposing credentials or uploading user data.

    This is a notification check, not a silent binary replacement. Automatic
    installation is intentionally avoided because unsigned binaries cannot be
    safely trusted; the UI links to the signed/verified release page instead.
    """
    if os.environ.get("ASTROLINK_DISABLE_UPDATE_CHECK", "").lower() in {"1", "true", "yes"}:
        return {"currentVersion": APP_VERSION, "updateAvailable": False, "disabled": True}
    url = f"https://api.github.com/repos/{UPDATE_REPOSITORY}/releases/latest"
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "AstroLink-Update-Checker"})
        with urllib.request.urlopen(request, timeout=3.0) as response:
            release = json.loads(response.read().decode("utf-8"))
        latest_tag = str(release.get("tag_name", "")).lstrip("v")
        def version_tuple(value: str) -> tuple[int, ...]:
            return tuple(int(part) for part in re.findall(r"\d+", value)[:4]) or (0,)
        assets = [{"name": a.get("name"), "url": a.get("browser_download_url")} for a in release.get("assets", [])]
        return {
            "currentVersion": APP_VERSION,
            "latestVersion": latest_tag,
            "updateAvailable": version_tuple(latest_tag) > version_tuple(APP_VERSION),
            "releaseUrl": release.get("html_url"),
            "assets": assets,
        }
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.info("Update check unavailable: %s", exc)
        return {"currentVersion": APP_VERSION, "updateAvailable": False, "available": False}


@app.post("/api/settings")
async def update_processing_settings(payload: Dict[str, Any], request: Request):
    """Updates preview-processing settings without changing the linear master."""
    _require_api_token(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Settings payload must be an object")
    return session.set_processing_options(
        reveal_deep_sky=payload.get("revealDeepSky"),
        clear_city_glow=payload.get("clearCityGlow"),
    )


@app.post("/api/reset")
async def reset_session(request: Request):
    """Resets current stacking session."""
    _require_api_token(request)
    session.reset()
    payload = {
        "type": "telemetry",
        "stackCount": 0,
        "totalExp": 0.0,
        "fwhm": 0.0,
        "snrGain": 1.0,
        "alertMessage": None,
        "preview": None,
        "intervalometerRunning": intervalometer.is_running,
    }
    await ws_manager.broadcast_json(payload)
    return {"status": "session_reset"}


@app.get("/api/license")
async def get_license_status():
    """Returns current offline cryptographic license status and limits."""
    return license_manager.status.to_dict()


@app.post("/api/license/activate")
async def activate_license(payload: Dict[str, Any], request: Request):
    """Activates an offline cryptographic license key."""
    _require_api_token(request)
    key = payload.get("key") or payload.get("license_key") or ""
    if not key:
        raise HTTPException(status_code=400, detail="Missing license key in payload")

    lic_status = license_manager.activate_license(key, persist=True)
    if not lic_status.is_valid:
        raise HTTPException(
            status_code=400,
            detail=lic_status.error or "Invalid cryptographic license key",
        )

    # Broadcast updated telemetry with new license status
    stack_count = session.stacker.total_frames_processed
    await ws_manager.broadcast_json({
        "type": "telemetry",
        "stackCount": stack_count,
        "totalExp": round(session.total_exp_seconds, 1),
        "fwhm": session.last_fwhm,
        "snrGain": round(math.sqrt(max(1, stack_count)), 2),
        "alertMessage": "License activated: Unlimited stacking unlocked.",
        "preview": session.last_preview_webp_b64,
        "license": lic_status.to_dict(),
        "intervalometerRunning": intervalometer.is_running,
    })

    return {
        "status": "activated",
        "license": lic_status.to_dict(),
    }


@app.post("/api/license/deactivate")
async def deactivate_license(request: Request):
    """Deactivates active license and reverts to community trial mode."""
    _require_api_token(request)
    license_manager.deactivate()
    return {
        "status": "deactivated",
        "license": license_manager.status.to_dict(),
    }


# ==========================================================================
# ==========================================================================
# Camera & Hardware Direct Detection API
# ==========================================================================

@app.get("/api/camera/detect")
async def detect_connected_cameras(request: Request):
    """Scans USB and local mounts across Windows, Linux, and macOS for cameras.
    
    Identifies DSLR PTP (Canon, Nikon, Sony), Astro CMOS (ZWO, QHY, SVBONY),
    and SD Card DCIM hot-folders without requiring a web browser on the camera.
    """
    _require_api_token(request)
    discovered = camera_detector.scan()
    return {
        "cameras": [c.to_dict() for c in discovered],
        "count": len(discovered),
        "platform": sys.platform,
        "gphoto_available": bool(shutil.which("gphoto2")),
        "recommendation": (
            "Ready for tethered capture."
            if discovered
            else "Connect camera via USB cable in Manual/Bulb mode, or insert camera SD card."
        ),
    }


@app.get("/api/camera/status")
async def get_camera_status(request: Request):
    """Returns real-time status of intervalometer and camera tether connection."""
    _require_api_token(request)
    return {
        "connected": intervalometer.is_connected,
        "running": intervalometer.is_running,
        "camera_mode": intervalometer.camera_mode,
        "current_frame": intervalometer.current_frame,
        "total_frames": intervalometer.total_frames,
        "last_error": intervalometer.last_error,
    }


# ==========================================================================
# Feedback Collection API (Jules Autonomous Bug Fixing with Screenshots)
# ==========================================================================

@app.post("/api/feedback")
async def submit_feedback(payload: Dict[str, Any]):
    """Submits user feedback with optional screenshot attachments for autonomous Jules triage."""
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Feedback message cannot be empty")

    category = payload.get("category", "general")
    severity = payload.get("severity", "medium")
    device_info = payload.get("device_info")
    attachments = payload.get("attachments", [])
    
    # Capture current telemetry snapshot automatically
    stack_count = session.stacker.total_frames_processed
    telemetry_snapshot = {
        "stackCount": stack_count,
        "totalExp": round(session.total_exp_seconds, 1),
        "fwhm": session.last_fwhm,
        "snrGain": round(math.sqrt(max(1, stack_count)), 2),
        "alertMessage": session.last_alert_message,
        "intervalometerRunning": intervalometer.is_running,
    }

    try:
        entry = feedback_manager.submit(
            category=category,
            message=message,
            severity=severity,
            device_info=device_info,
            telemetry_snapshot=telemetry_snapshot,
            attachments=attachments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "status": "submitted",
        "feedback_id": entry.id,
        "attachments_count": len(entry.attachments),
        "attachments": entry.attachments,
    }


@app.get("/api/feedback/attachment/{filename}")
async def get_feedback_attachment(filename: str, request: Request):
    """Safely serves an attached screenshot or diagnostic image."""
    _require_admin_token(request)
    path = feedback_manager.get_attachment_path(filename)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path)


@app.get("/api/feedback")
async def get_feedback(request: Request):
    """Returns all unresolved feedback entries and statistics."""
    _require_admin_token(request)
    return {
        "entries": feedback_manager.get_all(),
        "stats": feedback_manager.get_stats(),
    }


@app.get("/api/feedback/export")
async def export_feedback_for_jules(request: Request):
    """Exports unresolved, pending feedback as formatted GitHub Issues for Jules."""
    _require_admin_token(request)
    return {"issues": feedback_manager.export_for_jules()}


@app.post("/api/feedback/track")
async def track_user_feedback(payload: Dict[str, Any], request: Request):
    """Returns only reports matching caller-provided opaque feedback IDs."""
    # Tracking is intentionally public: IDs are random and users need to check
    # their own ticket without exposing the full feedback database.
    ids = payload.get("ids", [])
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="Expected list of ticket IDs")
    entries = feedback_manager.get_by_ids(ids)
    return {"reports": entries, "stats": feedback_manager.get_stats()}


@app.post("/api/feedback/update")
async def update_feedback_status(payload: Dict[str, Any], request: Request):
    """Updates ticket status (e.g. when Jules triages or closes an issue)."""
    _require_admin_token(request)
    feedback_id = payload.get("id")
    new_status = payload.get("status")
    issue_number = payload.get("issue_number")
    issue_url = payload.get("issue_url")
    notes = payload.get("notes")
    if not feedback_id or not new_status:
        raise HTTPException(status_code=400, detail="Missing id or status")

    success = feedback_manager.update_triage_status(
        feedback_id=feedback_id,
        status=new_status,
        issue_number=issue_number,
        issue_url=issue_url,
        notes=notes,
    )
    return {"success": success}


@app.post("/api/feedback/clear")
async def clear_resolved_feedback(request: Request):
    """Clears all resolved feedback entries (called after Jules processes them)."""
    _require_admin_token(request)
    cleared = feedback_manager.clear_resolved()
    return {"status": "cleared", "count": cleared}


def get_frontend_dist_dir() -> Optional[Path]:
    """Resolves the frontend dist directory in production bundle or dev server.

    Detects if running inside a PyInstaller frozen executable (sys.frozen + sys._MEIPASS)
    or standard development directory structure.
    """
    candidates = []
    # 1. PyInstaller frozen single-executable bundle
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
        candidates.extend([
            base_dir / "frontend" / "dist",
            base_dir / "dist",
        ])
    else:
        # 2. Local development checkout
        candidates.extend([
            PROJECT_ROOT / "frontend" / "dist",
            PROJECT_ROOT / "dist",
            Path("frontend/dist").resolve(),
            Path("dist").resolve(),
        ])

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "index.html").exists():
            return candidate
    return None


# Mount static production frontend if built
frontend_dist = get_frontend_dist_dir()
if frontend_dist:
    from fastapi.staticfiles import StaticFiles

    logger.info("Serving AstroLink production frontend from: %s", frontend_dist)
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    logger.warning("Frontend dist directory not found. Serving API and WebSocket only.")


def launch_desktop_app(host: str = "0.0.0.0", port: int = 8080, open_browser: bool = True) -> None:  # nosec B104
    """Starts Uvicorn server and automatically opens user's default browser."""
    import threading
    import time
    import webbrowser
    import uvicorn

    def _open_browser():
        url = f"http://localhost:{port}"
        start = time.time()
        while time.time() - start < 10.0:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    time.sleep(0.3)
                    logger.info("AstroLink live at %s. Opening default browser...", url)
                    webbrowser.open(url)
                    return
            except (OSError, ConnectionRefusedError):
                time.sleep(0.2)
        webbrowser.open(url)

    if open_browser:
        threading.Thread(target=_open_browser, daemon=True).start()

    logger.info("Starting AstroLink desktop engine on http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    launch_desktop_app()


