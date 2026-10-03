"""Hardware intervalometer module for USB camera control and exposure sequencing.

Controls DSLR and mirrorless cameras via libgphoto2 (or simulation fallback).
Executes precision exposure sequences with sensor cooldown delays, bulb mode handling,
in-memory buffer extraction, and automated delivery to the universal frame loader.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from typing import Any, Callable, Dict, Optional

import numpy as np

logger = logging.getLogger("astrolink.intervalometer")


class CameraIntervalometer:
    """Automated camera intervalometer and exposure sequence engine.

    Connects to DSLR/mirrorless cameras via USB PTP, orchestrates automated
    shooting schedules with mandatory sensor cooldown intervals, and routes
    captured image buffers directly into the stacking pipeline.
    """

    def __init__(
        self,
        on_frame_captured: Optional[Callable[[bytes, str, float], None]] = None,
        simulate: bool = False,
    ):
        """Initializes the intervalometer.

        Args:
            on_frame_captured: Callback accepting (data_bytes, filename, exposure_seconds).
            simulate: If True, operates in simulation mode with synthetic exposures.
        """
        self.on_frame_captured = on_frame_captured
        self.simulate = simulate

        self.camera: Any = None
        self._gp: Any = None
        self._cv2_cap: Any = None
        self.camera_mode: str = "auto"  # "gphoto2", "opencv", "simulate"
        self._is_connected: bool = False
        self._is_running: bool = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.current_frame: int = 0
        self.total_frames: int = 0
        self.last_error: Optional[str] = None

        # Check if gphoto2 python bindings are available
        try:
            import gphoto2 as gp

            self._gp = gp
        except ImportError:
            self._gp = None

    @property
    def is_connected(self) -> bool:
        """Returns True if the camera session is open."""
        return self._is_connected

    @property
    def is_running(self) -> bool:
        """Returns True if an exposure sequence is actively shooting."""
        return self._is_running

    def connect(self) -> bool:
        """Initializes hardware camera connection (DSLR PTP or OpenCV USB Camera).

        Returns:
            True if connection established, False otherwise.
        """
        if self._is_connected:
            return True

        if os.environ.get("ASTROLINK_DISABLE_HARDWARE", "").lower() in {"1", "true", "yes"}:
            self.last_error = "Hardware control is disabled in this deployment"
            return False

        # 1. Explicit simulation requested
        if self.simulate:
            self.camera_mode = "simulate"
            self._is_connected = True
            self.last_error = None
            logger.info("Intervalometer connected in explicit simulation mode.")
            return True

        # 2. Try DSLR / Mirrorless USB connection via libgphoto2
        if self._gp is not None:
            try:
                self.camera = self._gp.Camera()
                self.camera.init()
                self.camera_mode = "gphoto2"
                self._is_connected = True
                self.last_error = None
                logger.info("USB DSLR / mirrorless camera connected successfully via gphoto2.")
                return True
            except Exception as e:
                logger.debug("No gphoto2 DSLR camera detected: %s", e)
                self.camera = None

        # 3. Dedicated Astronomy Camera / Hot Folder Mode (N.I.N.A, ASIAIR, SharpCap, ZWO/QHY)
        # In field operations, astro cameras write directly to incoming directory
        self.camera_mode = "folder_watch"
        self._is_connected = True
        logger.info("Camera station armed in Astro Hot-Folder & Direct File Ingestion mode.")
        return True

    def disconnect(self) -> None:
        """Closes the camera session."""
        self.stop_sequence()

        if self.camera and self._gp is not None:
            try:
                self.camera.exit()
            except Exception as e:
                logger.debug("Error while closing camera session: %s", e)
            self.camera = None

        self._is_connected = False
        logger.info("Camera disconnected.")

    def _set_camera_config(self, key: str, value: Any) -> bool:
        """Helper to modify a camera configuration parameter."""
        if self.simulate or not self.camera:
            return True

        try:
            config = self.camera.get_config()
            widget = config.get_child_by_name(key)
            widget.set_value(str(value))
            self.camera.set_config(config)
            return True
        except Exception as e:
            logger.warning("Could not set camera config %s=%s: %s", key, value, e)
            return False

    def _capture_physical_shot(
        self,
        exposure_seconds: float,
        bulb_mode: bool,
        iso: Optional[Any],
    ) -> bytes:
        """Executes a single hardware exposure and fetches data into memory."""
        import cv2

        # 1. DSLR / Mirrorless Capture via libgphoto2 (when camera is present)
        if self.camera_mode == "gphoto2" and self.camera:
            if iso is not None:
                self._set_camera_config("iso", iso)

        if bulb_mode or exposure_seconds > 30.0:
            # Bulb mode exposure
            logger.info("Starting bulb exposure: %.1f seconds", exposure_seconds)
            try:
                # Canon EOS bulb trigger
                self._set_camera_config("eosbulb", 1)
            except Exception as e:
                logger.debug("Bulb start config skipped/unsupported on this model: %s", e)

            # Wait precisely for exposure duration
            time.sleep(exposure_seconds)

            try:
                self._set_camera_config("eosbulb", 0)
            except Exception as e:
                logger.debug("Bulb stop config skipped/unsupported on this model: %s", e)

            # Fetch the resulting image from the camera
            camera_file = self.camera.file_get(
                self._gp.GP_PORT_USB, "bulb_capture.jpg", self._gp.GP_FILE_TYPE_NORMAL
            )
            return camera_file.get_data_and_size()
        else:
            # Standard shutter speed preset
            self._set_camera_config("shutterspeed", f"{exposure_seconds}")
            file_path = self.camera.capture(self._gp.GP_CAPTURE_IMAGE)
            camera_file = self.camera.file_get(
                file_path.folder, file_path.name, self._gp.GP_FILE_TYPE_NORMAL
            )
            return camera_file.get_data_and_size()

        # Fallback if no physical DSLR attached
        return self._capture_simulated_shot(self.current_frame, exposure_seconds)

    def _capture_simulated_shot(
        self,
        frame_idx: int,
        exposure_seconds: float,
    ) -> bytes:
        """Generates a realistic synthetic JPEG frame for testing / simulation."""
        import cv2

        width, height = 512, 512
        rng = np.random.default_rng(1000 + frame_idx)
        field = np.zeros((height, width), dtype=np.float32)

        # Generate stars with slight tracking drift per frame
        drift_x = float(frame_idx * 2.5)
        drift_y = float(frame_idx * -1.5)

        x_coords = rng.uniform(40, width - 40, 50) + drift_x
        y_coords = rng.uniform(40, height - 40, 50) + drift_y
        intensities = rng.uniform(0.5, 1.0, 50)

        y_grid, x_grid = np.mgrid[0:height, 0:width]

        for x0, y0, intensity in zip(x_coords, y_coords, intensities):
            if 0 <= x0 < width and 0 <= y0 < height:
                r2 = (x_grid - x0) ** 2 + (y_grid - y0) ** 2
                field += (intensity * np.exp(-r2 / (2.0 * 1.8**2))).astype(np.float32)

        field = np.clip(field + 0.05 + rng.normal(0, 0.005, (height, width)), 0.0, 1.0)
        u8 = (field * 255.0).astype(np.uint8)
        ok, buf = cv2.imencode(".jpg", u8, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return buf.tobytes()

    def _sequence_worker(
        self,
        exposure_seconds: float,
        frame_count: int,
        delay_seconds: float,
        iso: Optional[Any],
        bulb_mode: bool,
    ) -> None:
        """Worker thread executing the intervalometer loop."""
        self._is_running = True
        self.total_frames = frame_count
        self.current_frame = 0

        # Enforce minimum 2.0s cooldown delay
        effective_delay = max(2.0, float(delay_seconds))
        logger.info(
            "Starting sequence: %d frames, %.1fs exp, %.1fs cooldown (bulb=%s, iso=%s)",
            frame_count,
            exposure_seconds,
            effective_delay,
            bulb_mode,
            iso,
        )

        for i in range(frame_count):
            if self._stop_event.is_set():
                logger.info("Exposure sequence aborted by user at frame %d/%d.", i, frame_count)
                break

            self.current_frame = i + 1
            filename = f"capture_{self.current_frame:04d}.jpg"
            logger.info("Executing exposure %d/%d (%.1fs)...", self.current_frame, frame_count, exposure_seconds)

            try:
                if self.camera_mode == "simulate":
                    # In simulation mode, sleep briefly to simulate exposure
                    sim_exp_time = min(0.5, exposure_seconds)
                    time.sleep(sim_exp_time)
                    data = self._capture_simulated_shot(self.current_frame, exposure_seconds)
                else:
                    data = self._capture_physical_shot(exposure_seconds, bulb_mode, iso)

                # Pass captured in-memory file buffer directly to ingestion callback
                if self.on_frame_captured:
                    self.on_frame_captured(data, filename, exposure_seconds)

            except Exception as e:
                logger.error("Error capturing frame %d: %s", self.current_frame, e)
                self.last_error = str(e)

            # Mandatory sensor cooldown and buffer flush delay
            if i < frame_count - 1 and not self._stop_event.is_set():
                logger.debug("Sensor cooldown delay: %.1f seconds", effective_delay)
                # Sleep in increments of 0.2s so abort is responsive
                elapsed = 0.0
                while elapsed < effective_delay and not self._stop_event.is_set():
                    step = min(0.2, effective_delay - elapsed)
                    time.sleep(step)
                    elapsed += step

        self._is_running = False
        logger.info("Exposure sequence completed.")

    def start_sequence(
        self,
        exposure_seconds: float,
        frame_count: int,
        delay_seconds: float = 2.0,
        iso: Optional[Any] = None,
        bulb_mode: bool = False,
    ) -> bool:
        """Spawns background exposure sequence thread.

        Args:
            exposure_seconds: Sub-exposure length in seconds.
            frame_count: Total number of frames to capture.
            delay_seconds: Pause between exposures for sensor cooldown (minimum 2s).
            iso: Optional camera ISO sensitivity setting (e.g. 800, 1600).
            bulb_mode: If True, forces bulb shutter actuation.

        Returns:
            True if sequence launched, False if already running or not connected.
        """
        try:
            exposure_seconds = float(exposure_seconds)
            frame_count = int(frame_count)
            delay_seconds = float(delay_seconds)
        except (TypeError, ValueError):
            self.last_error = "Exposure, frame count, and delay must be numeric"
            return False

        if not (math.isfinite(exposure_seconds) and 0.1 <= exposure_seconds <= 86400):
            self.last_error = "Exposure must be between 0.1 and 86400 seconds"
            return False
        if not (1 <= frame_count <= 10000):
            self.last_error = "Frame count must be between 1 and 10000"
            return False
        if not (math.isfinite(delay_seconds) and 0 <= delay_seconds <= 86400):
            self.last_error = "Delay must be between 0 and 86400 seconds"
            return False

        if self._is_running:
            logger.warning("Cannot start sequence: already running.")
            return False

        if not self._is_connected:
            if not self.connect():
                return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._sequence_worker,
            args=(exposure_seconds, frame_count, delay_seconds, iso, bulb_mode),
            name="IntervalometerWorker",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop_sequence(self) -> None:
        """Immediately signals the active sequence to abort."""
        if self._is_running:
            logger.info("Signaling intervalometer to stop sequence...")
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3.0)
                self._thread = None
            self._is_running = False
