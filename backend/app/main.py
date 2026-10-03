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
import io
import json
import logging
import math
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure backend package can be resolved
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
from backend.app.pipeline.ingest import load_universal_frame
from backend.app.pipeline.satellites import detect_satellite_streaks
from backend.app.pipeline.stacker import WelfordStacker
from backend.app.pipeline.stretch import auto_stretch

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("astrolink.server")


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

    def reset(self) -> None:
        """Resets the live stacker and telemetry."""
        self.stacker.reset()
        self.fwhm_tracker = RollingFWHMTracker(maxlen=5, blur_threshold_ratio=0.25)
        self.ref_frame = None
        self.total_exp_seconds = 0.0
        self.last_fwhm = 0.0
        self.last_alert_message = None
        self.last_preview_webp_b64 = None
        self.last_preview_webp_bytes = None
        self.last_frame_name = None

    def process_sub_exposure(
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
            frame = image_bytes.astype(np.float32)
            if frame.max() > 1.0:
                frame /= 255.0
        else:
            frame = load_universal_frame(image_bytes)

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

        # 7. Background Gradient Removal
        stacked_raw = self.stacker.get_result()
        clean_stacked = remove_background_gradient(stacked_raw, order=2)

        # 8. Nonlinear Display AutoStretch (MTF + Saturation)
        stretched_preview = auto_stretch(clean_stacked, target_bg=0.25, preserve_saturation=(clean_stacked.ndim == 3))

        # 9. Scale to 1080p display preview
        prev_h, prev_w = stretched_preview.shape[:2]
        scale_1080p = min(1.0, 1920.0 / prev_w, 1080.0 / prev_h)
        if scale_1080p < 1.0:
            target_w = int(round(prev_w * scale_1080p))
            target_h = int(round(prev_h * scale_1080p))
            preview_1080p = cv2.resize(stretched_preview, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            preview_1080p = stretched_preview

        # Encode to WebP
        ok, webp_buffer = cv2.imencode(".webp", preview_1080p, [cv2.IMWRITE_WEBP_QUALITY, 85])
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
                port=8080,
                server="astrolink.local.",
                properties={"path": "/"},
            )
            zeroconf_instance.register_service(service_info)
            logger.info("Zero-Config mDNS broadcast active: astrolink.local:8080 on %s", local_ip)
        except Exception as e:
            logger.warning("Zero-Config mDNS registration not available or skipped: %s", e)

    import threading
    threading.Thread(target=_start_mdns, daemon=True, name="mDNS-Broadcast").start()

    # Initialize Hardware Tethering Daemon
    def on_tether_frame(frame: CapturedFrame) -> None:
        logger.info("Hardware tether triggered frame ingestion: %s", frame.filename)
        _on_intervalometer_frame_captured(frame.data, frame.filename, 30.0)

    tether_daemon = GPhotoTetherDaemon(on_frame_callback=on_tether_frame, simulate=True)
    tether_daemon.start()

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

# CORS setup allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
async def upload_frame(file: UploadFile = File(...)):
    """Ingests multipart sub-exposures through universal decoding into WelfordStacker.

    Supports FITS, DSLR RAWs, Linear DNGs, TIFF, JPEG, PNG, and WebP formats.
    Broadcasts real-time telemetry and 1080p WebP previews across WebSocket clients.
    """
    try:
        data = await file.read()
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

    except Exception as e:
        logger.error("Failed to ingest frame: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Frame ingestion failed: {str(e)}",
        )


@app.get("/api/export")
async def export_master_stack():
    """Exports current master stack as an uncompressed 16-bit TIFF using tifffile."""
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
                command = cmd_data.get("command") or cmd_data.get("action") or command
            except Exception:
                pass

            # Handle WebSocket Commands
            if command == "START_SEQUENCE":
                exposure_seconds = float(cmd_data.get("exposure_seconds", 30.0))
                frame_count = int(cmd_data.get("frame_count", 10))
                delay_seconds = float(cmd_data.get("delay_seconds", 2.0))
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


@app.post("/api/reset")
async def reset_session():
    """Resets current stacking session."""
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
async def activate_license(payload: Dict[str, Any]):
    """Activates an offline cryptographic license key."""
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
async def deactivate_license():
    """Deactivates active license and reverts to community trial mode."""
    license_manager.deactivate()
    return {
        "status": "deactivated",
        "license": license_manager.status.to_dict(),
    }


# ==========================================================================
# Feedback Collection API (Jules Autonomous Bug Fixing)
# ==========================================================================

@app.post("/api/feedback")
async def submit_feedback(payload: Dict[str, Any]):
    """Submits user feedback for autonomous Jules triage and resolution."""
    message = payload.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Feedback message cannot be empty")

    category = payload.get("category", "general")
    severity = payload.get("severity", "medium")
    device_info = payload.get("device_info")
    
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

    entry = feedback_manager.submit(
        category=category,
        message=message,
        severity=severity,
        device_info=device_info,
        telemetry_snapshot=telemetry_snapshot,
    )
    return {"status": "submitted", "feedback_id": entry.id}


@app.get("/api/feedback")
async def get_feedback():
    """Returns all unresolved feedback entries and statistics."""
    return {
        "entries": feedback_manager.get_all(),
        "stats": feedback_manager.get_stats(),
    }


@app.get("/api/feedback/export")
async def export_feedback_for_jules():
    """Exports unresolved, pending feedback as formatted GitHub Issues for Jules."""
    return {"issues": feedback_manager.export_for_jules()}


@app.post("/api/feedback/track")
async def track_user_feedback(payload: Dict[str, Any]):
    """Returns status, GitHub issue links, and resolution notes for user-submitted ticket IDs."""
    ids = payload.get("ids", [])
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="Expected list of ticket IDs")
    entries = feedback_manager.get_by_ids(ids)
    return {"reports": entries, "stats": feedback_manager.get_stats()}


@app.post("/api/feedback/update")
async def update_feedback_status(payload: Dict[str, Any]):
    """Updates ticket status (e.g. when Jules triages or closes an issue)."""
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
async def clear_resolved_feedback():
    """Clears all resolved feedback entries (called after Jules processes them)."""
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


def launch_desktop_app(host: str = "0.0.0.0", port: int = 8080, open_browser: bool = True) -> None:
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


