"""Universal astronomical sub-exposure ingestion module.

Normalizes diverse astronomical and photography file formats (FITS, DSLR RAWs,
Linear DNGs, TIFF, JPEG, PNG, WebP) into a standardized 3-channel (H, W, 3)
float32 array scaled to [0.0, 1.0].
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Union

import cv2
import numpy as np

logger = logging.getLogger("astrolink.ingest")


def _normalize_array_to_float32(arr: np.ndarray) -> np.ndarray:
    """Normalizes an arbitrary scalar/integer array to float32 [0.0, 1.0]."""
    if arr.dtype == np.uint8:
        return arr.astype(np.float32) / 255.0
    if arr.dtype == np.uint16:
        return arr.astype(np.float32) / 65535.0
    if arr.dtype == np.int16:
        shifted = arr.astype(np.float32) + 32768.0
        return np.clip(shifted / 65535.0, 0.0, 1.0)
    if arr.dtype in (np.int32, np.uint32):
        max_val = float(np.max(arr)) if np.max(arr) > 0 else 1.0
        return np.clip(arr.astype(np.float32) / max_val, 0.0, 1.0)

    # Floating point inputs
    f32 = arr.astype(np.float32)
    max_val = float(np.max(f32))
    min_val = float(np.min(f32))

    if max_val > 255.0:
        return np.clip(f32 / 65535.0, 0.0, 1.0)
    if max_val > 1.0:
        return np.clip(f32 / 255.0, 0.0, 1.0)
    if min_val < 0.0:
        return np.clip((f32 - min_val) / max(1e-6, max_val - min_val), 0.0, 1.0)

    return np.clip(f32, 0.0, 1.0)


def _ensure_3_channel_rgb(arr: np.ndarray) -> np.ndarray:
    """Ensures input array has shape (H, W, 3)."""
    if arr.ndim == 2:
        return np.repeat(arr[:, :, np.newaxis], 3, axis=2)

    if arr.ndim == 3:
        # Check channel dimension position: if shape is (3, H, W) or (C, H, W)
        if arr.shape[0] in (1, 3, 4) and arr.shape[2] > 4:
            arr = np.transpose(arr, (1, 2, 0))

        if arr.shape[2] == 1:
            return np.repeat(arr, 3, axis=2)
        if arr.shape[2] == 3:
            return arr
        if arr.shape[2] == 4:
            # Drop alpha channel
            return arr[:, :, :3]

    raise ValueError(f"Unsupported image shape for 3-channel RGB conversion: {arr.shape}")


def _detect_format_from_bytes(data: bytes) -> str:
    """Infers file format from leading magic bytes."""
    if len(data) >= 8:
        if data.startswith(b"SIMPLE  =") or data.startswith(b"XTENSION="):
            return "fits"
        if data[:4] == b"\x89PNG":
            return "png"
        if data[:3] == b"\xff\xd8\xff":
            return "jpeg"
        if data[:4] in (b"II*\x00", b"MM\x00*"):
            # Could be TIFF, CR2, NEF, ARW, or DNG
            if len(data) >= 12 and data[8:10] == b"CR":
                return "raw"
            return "tiff"
        if data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
            return "webp"
        if data.startswith(b"FUJIFILM"):
            return "raw"

    return "unknown"


def _load_fits(data_or_path: Union[bytes, str, Path]) -> np.ndarray:
    """Loads FITS astronomical file, flips vertically (np.flipud), and expands to RGB."""
    try:
        from astropy.io import fits
    except ImportError:
        raise ImportError("astropy is required for FITS decoding. Install via: pip install astropy")

    if isinstance(data_or_path, (str, Path)):
        hdul = fits.open(data_or_path)
    else:
        hdul = fits.open(io.BytesIO(data_or_path))

    with hdul:
        # Find primary or first valid image HDU
        data = None
        for hdu in hdul:
            if hdu.data is not None and isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2:
                data = hdu.data
                break

        if data is None:
            raise ValueError("No valid 2D/3D image data array found in FITS HDUs.")

    # Squeeze empty leading dimensions if shape is e.g. (1, H, W)
    data = np.squeeze(data)

    # In astrophotography, FITS coordinates have y=0 at bottom.
    # Flip vertically to align with optical image orientation
    flipped = np.flipud(data)

    norm_f32 = _normalize_array_to_float32(flipped)
    return _ensure_3_channel_rgb(norm_f32)


def _load_raw(data_or_path: Union[bytes, str, Path]) -> np.ndarray:
    """Loads camera RAW (CR2, CR3, NEF, ARW, RAF, DNG) via rawpy."""
    try:
        import rawpy
    except ImportError:
        raise ImportError("rawpy is required for camera RAW decoding. Install via: pip install rawpy")

    if isinstance(data_or_path, (str, Path)):
        raw_ctx = rawpy.imread(str(data_or_path))
    else:
        raw_ctx = rawpy.imread(io.BytesIO(data_or_path))

    with raw_ctx as raw:
        # Detect whether the frame is a Bayer mosaic or Linear DNG (e.g., Apple ProRAW)
        is_linear_dng = False
        try:
            # Linear DNGs typically have 3 or 4 colors per pixel and are not flat bayer patterns
            if hasattr(raw, "raw_type") and hasattr(rawpy, "RawType"):
                if raw.raw_type != rawpy.RawType.Bayer:
                    is_linear_dng = True
            elif hasattr(raw, "num_colors") and raw.num_colors == 3 and not getattr(raw, "is_bayer", True):
                is_linear_dng = True
        except Exception:
            is_linear_dng = False

        if is_linear_dng:
            # Linear DNG (e.g., Apple ProRAW): postprocess with use_camera_wb=True, no_auto_bright=True
            rgb_u16 = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=True,
                output_bps=16,
            )
        else:
            # Standard Bayer mosaic: postprocess with gamma=(1,1), no_auto_bright=True, use_camera_wb=False, output_bps=16
            rgb_u16 = raw.postprocess(
                gamma=(1, 1),
                no_auto_bright=True,
                use_camera_wb=False,
                output_bps=16,
            )

    f32 = rgb_u16.astype(np.float32) / 65535.0
    return _ensure_3_channel_rgb(f32)


def _load_tiff(data_or_path: Union[bytes, str, Path]) -> np.ndarray:
    """Loads TIFF file via tifffile, normalizing based on bit depth to float32."""
    try:
        import tifffile
    except ImportError:
        raise ImportError("tifffile is required for TIFF decoding. Install via: pip install tifffile")

    if isinstance(data_or_path, (str, Path)):
        img = tifffile.imread(str(data_or_path))
    else:
        with io.BytesIO(data_or_path) as buf:
            img = tifffile.imread(buf)

    norm_f32 = _normalize_array_to_float32(img)
    return _ensure_3_channel_rgb(norm_f32)


def _load_opencv(data_or_path: Union[bytes, str, Path]) -> np.ndarray:
    """Loads standard images (JPEG, PNG, WebP) via OpenCV and converts to RGB float32."""
    if isinstance(data_or_path, (str, Path)):
        decoded = cv2.imread(str(data_or_path), cv2.IMREAD_UNCHANGED)
    else:
        np_arr = np.frombuffer(data_or_path, dtype=np.uint8)
        decoded = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)

    if decoded is None:
        raise ValueError("OpenCV failed to decode image data.")

    # Convert color channel order from BGR(A) to RGB
    if decoded.ndim == 2:
        rgb = cv2.cvtColor(decoded, cv2.COLOR_GRAY2RGB)
    elif decoded.ndim == 3:
        if decoded.shape[2] == 3:
            rgb = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
        elif decoded.shape[2] == 4:
            rgb = cv2.cvtColor(decoded, cv2.COLOR_BGRA2RGB)
        else:
            rgb = decoded
    else:
        rgb = decoded

    norm_f32 = _normalize_array_to_float32(rgb)
    return _ensure_3_channel_rgb(norm_f32)


def load_universal_frame(file_bytes_or_path: Union[bytes, str, Path]) -> np.ndarray:
    """Universal sub-exposure loader.

    Converts FITS, camera RAWs, Linear DNGs, TIFFs, JPEGs, PNGs, and WebPs
    into an identical format: 3-channel (H, W, 3) np.float32 in range [0.0, 1.0].

    Args:
        file_bytes_or_path: In-memory bytes buffer or file system path.

    Returns:
        Standardized numpy array of shape (H, W, 3), dtype np.float32, values in [0.0, 1.0].
    """
    ext = ""
    if isinstance(file_bytes_or_path, (str, Path)):
        p = Path(file_bytes_or_path)
        ext = p.suffix.lower()
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {p}")

    # Determine format by extension or byte header
    detected = ""
    if ext in (".fits", ".fit"):
        detected = "fits"
    elif ext in (".cr2", ".cr3", ".nef", ".arw", ".raf", ".dng"):
        detected = "raw"
    elif ext in (".tif", ".tiff"):
        detected = "tiff"
    elif ext in (".jpg", ".jpeg", ".png", ".webp"):
        detected = "opencv"
    else:
        # Suffix not definitive; inspect magic bytes if input is bytes
        if isinstance(file_bytes_or_path, bytes):
            detected = _detect_format_from_bytes(file_bytes_or_path)
        else:
            # Read first 32 bytes of path to detect
            try:
                with open(file_bytes_or_path, "rb") as f:
                    header = f.read(32)
                detected = _detect_format_from_bytes(header)
            except Exception:
                detected = "unknown"

    # Route to specialized loader with cascading fallbacks
    if detected == "fits":
        return _load_fits(file_bytes_or_path)

    if detected == "raw":
        try:
            return _load_raw(file_bytes_or_path)
        except Exception as e:
            logger.debug("rawpy loading failed, attempting TIFF/OpenCV fallback: %s", e)
            try:
                return _load_tiff(file_bytes_or_path)
            except Exception:
                return _load_opencv(file_bytes_or_path)

    if detected == "tiff":
        try:
            return _load_tiff(file_bytes_or_path)
        except Exception as e:
            logger.debug("tifffile loading failed, attempting OpenCV fallback: %s", e)
            return _load_opencv(file_bytes_or_path)

    # Default to OpenCV
    try:
        return _load_opencv(file_bytes_or_path)
    except Exception as e:
        # Final attempts: try TIFF then FITS
        try:
            return _load_tiff(file_bytes_or_path)
        except Exception:
            try:
                return _load_fits(file_bytes_or_path)
            except Exception:
                raise ValueError(f"Failed to decode sub-exposure using any universal loader: {e}")
