"""Hardware tethering daemon wrapping gphoto2 for USB camera capture.

Manages background gphoto2 tethered capture processes with custom hook scripts.
When a DSLR or mirrorless camera shutter triggers over USB, sub-exposures are
immediately read into RAM buffers and passed to the ingestion queue.
"""

from __future__ import annotations

import logging
import os
import queue
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("astrolink.tether")


@dataclass
class CapturedFrame:
    """Represents a sub-exposure ingested from the camera hardware tether."""

    filename: str
    data: bytes
    timestamp: float
    source: str = "gphoto2"


class GPhotoTetherDaemon:
    """Background daemon wrapping `gphoto2 --capture-tethered --keep --hook-script=...`.

    Monitors USB camera tethering events, ingests incoming RAW/JPEG frames
    directly into memory buffers, and dispatches them to a processing queue.
    """

    def __init__(
        self,
        ingest_queue: Optional[queue.Queue[CapturedFrame]] = None,
        on_frame_callback: Optional[Callable[[CapturedFrame], None]] = None,
        watch_dir: Optional[Path] = None,
        simulate: bool = False,
    ):
        """Initializes the tethering daemon.

        Args:
            ingest_queue: Thread-safe queue where captured frames are placed.
            on_frame_callback: Optional callback invoked immediately upon frame ingestion.
            watch_dir: Directory where tethered frames are written by gphoto2.
            simulate: If True, operates in simulation mode without invoking gphoto2 binary.
        """
        self.ingest_queue = ingest_queue or queue.Queue()
        self.on_frame_callback = on_frame_callback
        self.simulate = simulate

        self._temp_dir = tempfile.mkdtemp(prefix="astrolink_tether_")
        self.watch_dir = Path(watch_dir or self._temp_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._hook_script_path: Optional[Path] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Returns True if the daemon worker thread is active."""
        return self._is_running

    def _create_hook_script(self) -> Path:
        """Generates an IPC hook script compatible with gphoto2 --hook-script."""
        # gphoto2 calls the hook script with action in $ACTION (or $1) and file path in $ARGUMENT (or $2)
        # We generate a Python hook script executable across all platforms.
        ipc_file = self.watch_dir / ".gphoto_events.txt"

        if sys.platform == "win32":
            # Batch script wrapper on Windows
            script_path = self.watch_dir / "gphoto_hook.bat"
            content = f"""@echo off
if "%ACTION%"=="download" (
    echo %ARGUMENT%>> "{ipc_file}"
)
if "%1"=="download" (
    echo %2>> "{ipc_file}"
)
"""
            script_path.write_text(content, encoding="utf-8")
        else:
            # Shell script on Linux / macOS
            script_path = self.watch_dir / "gphoto_hook.sh"
            content = f"""#!/bin/sh
if [ "$ACTION" = "download" ]; then
    echo "$ARGUMENT" >> "{ipc_file}"
fi
if [ "$1" = "download" ]; then
    echo "$2" >> "{ipc_file}"
fi
"""
            script_path.write_text(content, encoding="utf-8")
            script_path.chmod(0o755)

        return script_path

    def _worker(self) -> None:
        """Background thread monitoring gphoto2 and ingesting captured files into RAM."""
        self._is_running = True
        logger.info("Tether daemon background worker started.")

        gphoto_bin = shutil.which("gphoto2")
        ipc_file = self.watch_dir / ".gphoto_events.txt"

        if not self.simulate and gphoto_bin:
            self._hook_script_path = self._create_hook_script()
            cmd = [
                gphoto_bin,
                "--capture-tethered",
                "--keep",
                f"--hook-script={self._hook_script_path}",
            ]
            logger.info("Spawning gphoto2 process: %s (cwd=%s)", " ".join(cmd), self.watch_dir)
            try:
                self._process = subprocess.Popen(  # nosec B603
                    cmd,
                    cwd=str(self.watch_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except Exception as e:
                logger.error("Failed to launch gphoto2 subprocess: %s", e)
                self._process = None
        else:
            if not self.simulate:
                logger.warning(
                    "gphoto2 CLI not found on PATH. Falling back to folder-watcher / simulation mode."
                )

        seen_files: set[Path] = set()

        while not self._stop_event.is_set():
            # Check IPC event log from hook script
            if ipc_file.exists():
                try:
                    lines = ipc_file.read_text(encoding="utf-8").splitlines()
                    # Truncate after reading
                    ipc_file.write_text("", encoding="utf-8")
                    for line in lines:
                        target_path = Path(line.strip())
                        if not target_path.is_absolute():
                            target_path = self.watch_dir / target_path
                        if target_path.exists() and target_path not in seen_files:
                            self._ingest_file(target_path)
                            seen_files.add(target_path)
                except Exception as e:
                    logger.debug("Error processing hook IPC log: %s", e)

            # Also scan watch_dir directly for any newly written sub-exposures
            try:
                for entry in self.watch_dir.iterdir():
                    if entry.is_file() and not entry.name.startswith("."):
                        suffix = entry.suffix.lower()
                        if suffix in (".cr2", ".cr3", ".nef", ".arw", ".dng", ".jpg", ".jpeg", ".tif", ".tiff", ".fits"):
                            if entry not in seen_files:
                                # Ensure file is completely written (stable size)
                                try:
                                    size1 = entry.stat().st_size
                                    time.sleep(0.05)
                                    size2 = entry.stat().st_size
                                    if size1 == size2 and size1 > 0:
                                        self._ingest_file(entry)
                                        seen_files.add(entry)
                                except (OSError, FileNotFoundError):
                                    pass
            except Exception as e:
                logger.debug("Error scanning tether watch directory: %s", e)

            time.sleep(0.1)

        # Cleanup subprocess
        if self._process and self._process.poll() is None:
            logger.info("Terminating gphoto2 tether process...")
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()

        self._is_running = False
        logger.info("Tether daemon background worker terminated.")

    def _ingest_file(self, file_path: Path) -> None:
        """Reads file immediately into RAM buffer and places onto ingestion queue."""
        try:
            logger.info("Ingesting camera sub-exposure into RAM: %s", file_path.name)
            data = file_path.read_bytes()
            frame = CapturedFrame(
                filename=file_path.name,
                data=data,
                timestamp=time.time(),
                source="gphoto2",
            )
            self.ingest_queue.put(frame)
            if self.on_frame_callback:
                self.on_frame_callback(frame)
        except Exception as e:
            logger.error("Failed to ingest frame from %s: %s", file_path, e)

    def inject_simulated_frame(self, filename: str, data: bytes) -> CapturedFrame:
        """Manually injects a frame into the tether queue for testing or simulation."""
        frame = CapturedFrame(
            filename=filename,
            data=data,
            timestamp=time.time(),
            source="simulated",
        )
        self.ingest_queue.put(frame)
        if self.on_frame_callback:
            self.on_frame_callback(frame)
        return frame

    def start(self) -> None:
        """Starts the background tethering daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Tether daemon is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="GPhotoTetherWorker")
        self._thread.start()

    def stop(self) -> None:
        """Stops the background tethering daemon thread and cleans up resources."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

        # Clean temporary directory
        if self._temp_dir and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
