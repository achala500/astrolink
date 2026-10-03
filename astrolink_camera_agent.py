#!/usr/bin/env python3
"""AstroLink Standalone Camera Node & Multi-OS Field Bridge.

Run this script on ANY computer or single-board computer connected to your DSLR:
- Linux / Raspberry Pi (mounted at telescope)
- macOS (MacBook in the field)
- Windows (Field laptop or mini PC)

Functionality:
1. Auto-discovers the AstroLink Field Station over local network via mDNS (Zeroconf) or direct IP.
2. Auto-detects connected USB DSLRs/Mirrorless cameras (Canon, Nikon, Sony, Fuji, ZWO, QHY) via PTP.
3. Automatically ingests sub-exposures (RAW, FITS, TIFF, JPEG) as they are shot and streams them
   directly to the AstroLink real-time stacking engine over local Wi-Fi / Ethernet.
4. Operates 100% offline with zero cloud or browser required on the camera node.

Usage:
    python astrolink_camera_agent.py
    python astrolink_camera_agent.py --server http://192.168.1.50:8080
    python astrolink_camera_agent.py --watch D:/DCIM/100CANON
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import socket
import subprocess  # nosec B404
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AstroLink-Node] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AstroLinkNode")

SUPPORTED_EXTENSIONS = {
    ".fits", ".fit", ".fts",
    ".cr2", ".cr3",
    ".nef",
    ".arw",
    ".dng",
    ".raf",
    ".orf",
    ".rw2",
    ".pef",
    ".tiff", ".tif",
    ".jpg", ".jpeg",
    ".png",
    ".webp",
}


def discover_server_via_mdns() -> Optional[str]:
    """Attempts to discover astrolink.local:8080 via mDNS."""
    try:
        from zeroconf import ServiceBrowser, Zeroconf

        logger.info("Scanning local Wi-Fi network for AstroLink Station via mDNS...")
        zc = Zeroconf()
        found_url = []

        class Listener:
            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info and info.addresses:
                    ip = socket.inet_ntoa(info.addresses[0])
                    port = info.port
                    found_url.append(f"http://{ip}:{port}")

            def update_service(self, zc, type_, name):
                pass

            def remove_service(self, zc, type_, name):
                pass

        browser = ServiceBrowser(zc, "_http._tcp.local.", Listener())
        time.sleep(2.0)
        zc.close()

        if found_url:
            return found_url[0]
    except Exception as e:
        logger.debug("mDNS discovery error: %s", e)

    # Fallback to local machine
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/api/license")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                return "http://127.0.0.1:8080"
    except Exception:
        pass

    return None


def upload_sub_exposure(server_url: str, file_path: Path) -> bool:
    """Uploads a raw sub-exposure to the AstroLink server via multipart POST."""
    endpoint = f"{server_url.rstrip('/')}/api/upload"
    boundary = "----AstroLinkBoundary" + str(int(time.time() * 1000))

    try:
        file_bytes = file_path.read_bytes()
        filename = file_path.name

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(endpoint, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("User-Agent", "AstroLink-Camera-Node/2.0")

        with urllib.request.urlopen(req, timeout=30.0) as response:
            if response.status in (200, 201):
                logger.info("Successfully ingested [%s] (%d KB) -> Live Stacking Active", filename, len(file_bytes) // 1024)
                return True
            else:
                logger.warning("Server returned HTTP %s for %s", response.status, filename)
                return False
    except urllib.error.HTTPError as e:
        logger.error("Upload rejected: HTTP %s - %s", e.code, e.reason)
        return False
    except Exception as err:
        logger.error("Failed to connect to AstroLink server at %s: %s", endpoint, err)
        return False


def run_gphoto2_tether(server_url: str, save_dir: Path) -> None:
    """Runs gphoto2 in tethered capture mode and immediately sends captured frames."""
    gphoto = shutil.which("gphoto2")
    if not gphoto:
        logger.error("gphoto2 CLI not found on PATH. Please install gphoto2 or use folder watch mode.")
        return

    logger.info("Starting gphoto2 USB tethered capture...")
    logger.info("Camera is ready! Take a photo on the camera or trigger sequence.")

    seen_files = set(save_dir.glob("*"))

    cmd = [
        gphoto,
        "--capture-tethered",
        "--keep",
    ]

    try:
        proc = subprocess.Popen(  # nosec B603
            cmd,
            cwd=str(save_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        while proc.poll() is None:
            time.sleep(0.5)
            current_files = set(save_dir.glob("*"))
            new_files = current_files - seen_files

            for nf in sorted(new_files, key=lambda f: f.stat().st_mtime):
                if nf.suffix.lower() in SUPPORTED_EXTENSIONS:
                    # Give camera time to finalize file writing
                    time.sleep(0.3)
                    upload_sub_exposure(server_url, nf)
                seen_files.add(nf)

    except KeyboardInterrupt:
        logger.info("Stopping camera tether...")
        proc.terminate()


def run_folder_watch(server_url: str, watch_dir: Path) -> None:
    """Monitors a local folder or SD card mount for new sub-exposures."""
    logger.info("Watching directory for new sub-exposures: %s", watch_dir.resolve())
    logger.info("Ready! Any photo saved here will be streamed to the AstroLink live stack.")

    seen_files = set(watch_dir.glob("*"))

    try:
        while True:
            time.sleep(1.0)
            current_files = set(watch_dir.glob("*"))
            new_files = current_files - seen_files

            for nf in sorted(new_files, key=lambda f: f.stat().st_mtime):
                if nf.suffix.lower() in SUPPORTED_EXTENSIONS:
                    time.sleep(0.5)  # Wait for file write to complete
                    upload_sub_exposure(server_url, nf)
                seen_files.add(nf)
    except KeyboardInterrupt:
        logger.info("Exiting folder watch...")


def main():
    parser = argparse.ArgumentParser(
        description="AstroLink Standalone Camera Node & Multi-OS Field Bridge"
    )
    parser.add_argument(
        "--server",
        type=str,
        default=None,
        help="AstroLink Server URL (e.g. http://192.168.1.50:8080). If omitted, auto-discovers via mDNS.",
    )
    parser.add_argument(
        "--watch",
        type=str,
        default=None,
        help="Directory to watch for incoming images (e.g. SD card path D:/DCIM/100CANON or N.I.N.A folder).",
    )
    parser.add_argument(
        "--tether",
        action="store_true",
        help="Force gphoto2 USB tethered capture mode.",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("   AstroLink Multi-OS Camera Bridge (Zero-Cloud Field Agent)   ")
    print("=" * 60)
    print(f"Platform: {sys.platform} ({os.name})")

    # 1. Resolve Server URL
    server_url = args.server
    if not server_url:
        server_url = discover_server_via_mdns()
        if not server_url:
            server_url = "http://localhost:8080"
            logger.info("Defaulting to local server: %s", server_url)
        else:
            logger.info("Auto-discovered AstroLink Server at: %s", server_url)
    else:
        logger.info("Using configured server: %s", server_url)

    # 2. Run Mode Selection
    if args.watch:
        watch_path = Path(args.watch)
        watch_path.mkdir(parents=True, exist_ok=True)
        run_folder_watch(server_url, watch_path)
    elif args.tether or shutil.which("gphoto2"):
        capture_dir = Path("./captured_sub_exposures")
        capture_dir.mkdir(parents=True, exist_ok=True)
        run_gphoto2_tether(server_url, capture_dir)
    else:
        # Default fallback to watching a local folder
        capture_dir = Path("./astro_hot_folder")
        capture_dir.mkdir(parents=True, exist_ok=True)
        logger.info("No gphoto2 CLI detected. Armed in Hot-Folder Watch mode: %s", capture_dir.resolve())
        run_folder_watch(server_url, capture_dir)


if __name__ == "__main__":
    main()
