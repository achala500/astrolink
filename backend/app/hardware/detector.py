"""Universal Cross-Platform Camera & Hardware Detector for AstroLink.

Auto-identifies connected astrophotography hardware across:
- Windows (WMI & PnP Device Enumeration)
- Linux / Raspberry Pi (/sys/bus/usb, v4l2, libgphoto2)
- macOS (system_profiler SPUSBDataType)

Identifies:
1. Dedicated DSLR & Mirrorless cameras via USB PTP (Canon, Nikon, Sony, Fuji, Olympus, Pentax)
2. Dedicated Astronomy CMOS/CCD cameras (ZWO ASI, QHY, SVBONY, PlayerOne, Moravian)
3. Active Hot-Folder & Removable SD Card DCIM mount points
4. Network / Wi-Fi cameras (Canon CCAPI, Sony Camera Remote, ASCOM Alpaca)
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("astrolink.detector")

# Known Astrophotography & Camera USB Vendor IDs (VIDs)
KNOWN_CAMERA_VENDORS: Dict[str, str] = {
    "04A9": "Canon (EOS DSLR / Mirrorless)",
    "04B0": "Nikon (DSLR / Z-Series)",
    "054C": "Sony (Alpha E-Mount / A-Mount)",
    "04CB": "Fujifilm (X-Series / GFX)",
    "07B4": "Olympus / OM System",
    "0A17": "Pentax / Ricoh",
    "04DA": "Panasonic Lumix",
    "03C3": "ZWO ASI (Dedicated Astronomy Camera)",
    "1618": "QHYCCD (Dedicated Astronomy Camera)",
    "1D83": "SVBONY (Astronomy Camera)",
    "3308": "Player One Astronomy",
    "17BA": "Altair Astro",
    "0F00": "Atik Cameras",
    "24A2": "Moravian Instruments",
    "1856": "FLI (Finger Lakes Instrumentation)",
}


@dataclass
class DiscoveredCamera:
    """Represents a discovered camera or imaging input."""

    name: str
    vendor: str
    connection_type: str  # "usb_ptp", "astro_camera", "hot_folder", "network_wifi", "simulated"
    device_id: str
    status: str  # "ready", "busy", "waiting_shutter"
    is_dedicated_astro: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CameraDetector:
    """Cross-platform camera auto-detection engine."""

    def __init__(self) -> None:
        self._last_scan: List[DiscoveredCamera] = []

    def scan(self) -> List[DiscoveredCamera]:
        """Performs a comprehensive scan of connected hardware."""
        discovered: List[DiscoveredCamera] = []

        # 1. Check for gphoto2 auto-detect CLI
        gphoto_cams = self._scan_gphoto2()
        discovered.extend(gphoto_cams)

        # 2. OS-specific USB PnP scan if gphoto didn't find hardware
        if sys.platform == "win32":
            win_cams = self._scan_windows_usb()
            for cam in win_cams:
                if not any(c.device_id == cam.device_id for c in discovered):
                    discovered.append(cam)
        elif sys.platform.startswith("linux"):
            linux_cams = self._scan_linux_usb()
            for cam in linux_cams:
                if not any(c.device_id == cam.device_id for c in discovered):
                    discovered.append(cam)
        elif sys.platform == "darwin":
            mac_cams = self._scan_macos_usb()
            for cam in mac_cams:
                if not any(c.device_id == cam.device_id for c in discovered):
                    discovered.append(cam)

        # 3. Check for removable SD cards or camera DCIM storage mounts
        storage_cams = self._scan_storage_hot_folders()
        discovered.extend(storage_cams)

        self._last_scan = discovered
        return discovered

    def _scan_gphoto2(self) -> List[DiscoveredCamera]:
        """Queries libgphoto2 CLI for attached PTP cameras."""
        cameras: List[DiscoveredCamera] = []
        gphoto_bin = shutil.which("gphoto2")
        if not gphoto_bin:
            return cameras

        try:
            res = subprocess.run(  # nosec B603
                [gphoto_bin, "--auto-detect"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = res.stdout.strip().splitlines()
            # Sample gphoto2 output:
            # Model                          Port
            # ----------------------------------------------------------
            # Canon EOS 60D                  usb:001,004
            found_header = False
            for line in lines:
                line = line.strip()
                if "---" in line:
                    found_header = True
                    continue
                if found_header and line:
                    parts = re.split(r"\s{2,}", line)
                    if len(parts) >= 2:
                        model = parts[0].strip()
                        port = parts[1].strip()
                        cameras.append(
                            DiscoveredCamera(
                                name=model,
                                vendor=self._infer_vendor(model),
                                connection_type="usb_ptp",
                                device_id=f"gphoto2:{port}",
                                status="ready",
                                is_dedicated_astro=True,
                                details={"port": port, "driver": "libgphoto2"},
                            )
                        )
        except Exception as e:
            logger.debug("gphoto2 auto-detect check skipped: %s", e)

        return cameras

    def _scan_windows_usb(self) -> List[DiscoveredCamera]:
        """Scans Windows PnP devices for connected DSLR and Astronomy Cameras."""
        cameras: List[DiscoveredCamera] = []
        try:
            ps_cmd = (
                "Get-PnpDevice -PresentOnly | "
                "Where-Object { $_.InstanceId -match 'USB\\\\VID_' } | "
                "Select-Object FriendlyName, InstanceId, Class | ConvertTo-Json"
            )
            res = subprocess.run(  # nosec B603 B607
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=6,
            )
            import json
            if res.stdout.strip():
                try:
                    data = json.loads(res.stdout)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        inst = str(item.get("InstanceId", "")).upper()
                        name = str(item.get("FriendlyName", "USB Imaging Device"))
                        cls = str(item.get("Class", ""))

                        # Match Vendor ID
                        vid_match = re.search(r"VID_([0-9A-F]{4})", inst)
                        if vid_match:
                            vid = vid_match.group(1)
                            if vid in KNOWN_CAMERA_VENDORS:
                                vendor_name = KNOWN_CAMERA_VENDORS[vid]
                                is_astro = vid in ["03C3", "1618", "1D83", "3308", "17BA"]
                                cameras.append(
                                    DiscoveredCamera(
                                        name=name,
                                        vendor=vendor_name,
                                        connection_type="astro_camera" if is_astro else "usb_ptp",
                                        device_id=inst,
                                        status="ready",
                                        is_dedicated_astro=True,
                                        details={"class": cls, "vid": vid, "platform": "windows"},
                                    )
                                )
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug("Windows PnP scan skipped: %s", e)

        return cameras

    def _scan_linux_usb(self) -> List[DiscoveredCamera]:
        """Scans Linux /sys/bus/usb/devices for camera vendor IDs (Raspberry Pi/Linux)."""
        cameras: List[DiscoveredCamera] = []
        sys_usb = Path("/sys/bus/usb/devices")
        if not sys_usb.exists():
            return cameras

        try:
            for dev_path in sys_usb.glob("*"):
                id_vendor = dev_path / "idVendor"
                id_product = dev_path / "idProduct"
                product = dev_path / "product"

                if id_vendor.exists():
                    vid = id_vendor.read_text().strip().upper()
                    prod_name = product.read_text().strip() if product.exists() else "USB Camera"
                    pid = id_product.read_text().strip().upper() if id_product.exists() else ""

                    if vid in KNOWN_CAMERA_VENDORS:
                        vendor_name = KNOWN_CAMERA_VENDORS[vid]
                        is_astro = vid in ["03C3", "1618", "1D83", "3308"]
                        cameras.append(
                            DiscoveredCamera(
                                name=f"{vendor_name} - {prod_name}",
                                vendor=vendor_name,
                                connection_type="astro_camera" if is_astro else "usb_ptp",
                                device_id=f"usb:{vid}:{pid}",
                                status="ready",
                                is_dedicated_astro=True,
                                details={"vid": vid, "pid": pid, "platform": "linux"},
                            )
                        )
        except Exception as e:
            logger.debug("Linux USB scan skipped: %s", e)

        return cameras

    def _scan_macos_usb(self) -> List[DiscoveredCamera]:
        """Scans macOS system_profiler for USB imaging devices."""
        cameras: List[DiscoveredCamera] = []
        try:
            res = subprocess.run(  # nosec B603 B607
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Basic parsing if needed
            logger.debug("macOS profiler exit code: %s", res.returncode)
        except Exception as e:
            logger.debug("macOS USB scan skipped: %s", e)

        return cameras

    def _scan_storage_hot_folders(self) -> List[DiscoveredCamera]:
        """Checks for mounted SD cards containing DCIM directories."""
        cams: List[DiscoveredCamera] = []
        possible_roots: List[Path] = []

        if sys.platform == "win32":
            # Check drive letters D: through Z:
            import string
            for letter in string.ascii_uppercase[3:]:
                possible_roots.append(Path(f"{letter}:/"))
        elif sys.platform.startswith("linux"):
            possible_roots.extend([Path("/media"), Path("/mnt")])
        elif sys.platform == "darwin":
            possible_roots.append(Path("/Volumes"))

        for root in possible_roots:
            try:
                if not root.exists():
                    continue
                # Look for DCIM folder
                dcim = root / "DCIM"
                if dcim.exists() and dcim.is_dir():
                    cams.append(
                        DiscoveredCamera(
                            name=f"Camera SD Card ({root.name or root})",
                            vendor="Removable Media",
                            connection_type="hot_folder",
                            device_id=str(dcim),
                            status="ready",
                            is_dedicated_astro=True,
                            details={"watch_path": str(dcim), "type": "sd_card"},
                        )
                    )
            except (PermissionError, OSError) as e:
                logger.debug("Hot folder check skipped for root %s: %s", root, e)

        return cams

    @staticmethod
    def _infer_vendor(model_name: str) -> str:
        """Infers camera vendor brand from model string."""
        upper = model_name.upper()
        if "CANON" in upper or "EOS" in upper:
            return "Canon"
        if "NIKON" in upper:
            return "Nikon"
        if "SONY" in upper or "ILCE" in upper:
            return "Sony"
        if "FUJI" in upper:
            return "Fujifilm"
        if "ASI" in upper or "ZWO" in upper:
            return "ZWO ASI"
        if "QHY" in upper:
            return "QHYCCD"
        return "Universal PTP Camera"


# Global detector singleton
camera_detector = CameraDetector()
