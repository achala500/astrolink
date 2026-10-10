# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for AstroLink.

Produces a standalone single-executable desktop application that bundles:
1. FastAPI + WebSocket backend engine
2. Uvicorn server runtime
3. Complete computer vision & astrophotography pipeline:
   - OpenCV (with bundled dynamic libraries/DLLs)
   - RawPy (with embedded LibRaw shared libraries)
   - Astropy (FITS processing & tables)
   - SciPy & NumPy
   - Tifffile & Zeroconf mDNS
   - Cryptography (Ed25519 offline licensing)
4. Compiled production React 18 + Tailwind frontend (frontend/dist) directly inside sys._MEIPASS
5. Desktop launcher that launches Uvicorn and opens the user's default browser to http://localhost:8080
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# Current project directory
SPECPATH = os.path.abspath(SPECPATH)

# 1. Collect all shared binaries/DLLs (OpenCV, LibRaw via RawPy, etc.)
binaries = []
binaries += collect_dynamic_libs("cv2")
binaries += collect_dynamic_libs("rawpy")

# 2. Collect package data files
datas = []
datas += collect_data_files("astropy.io")
datas += collect_data_files("scipy")
datas += collect_data_files("cryptography")
datas += collect_data_files("rawpy")
datas += collect_data_files("cv2")

# 3. Bundle compiled React frontend into sys._MEIPASS
frontend_dist_source = os.path.join(SPECPATH, "frontend", "dist")
if os.path.isdir(frontend_dist_source):
    # Place at both 'frontend/dist' and 'dist' for guaranteed resolution
    datas.append((frontend_dist_source, os.path.join("frontend", "dist")))
    datas.append((frontend_dist_source, "dist"))
    print(f"[PyInstaller Spec] Bundled production React frontend from {frontend_dist_source}")
else:
    print(f"[PyInstaller Spec] WARNING: frontend/dist not found at {frontend_dist_source}!")

# 4. Hidden imports for dynamic/lazy loaders
hiddenimports = [
    # Uvicorn internals
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # FastAPI & Starlette
    "fastapi",
    "fastapi.staticfiles",
    "fastapi.middleware.cors",
    "starlette",
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.websockets",
    # Computer vision & scientific stack
    "cv2",
    "numpy",
    "scipy",
    "scipy.signal",
    "scipy.ndimage",
    "scipy.optimize",
    "scipy.linalg",
    "rawpy",
    "astropy",
    "astropy.io.fits",
    "tifffile",
    # Hardware & networking
    "zeroconf",
    "ifaddr",
    # Cryptography
    "cryptography",
    "cryptography.hazmat.primitives.asymmetric.ed25519",
    "cryptography.hazmat.primitives.serialization",
    # Project modules
    "backend",
    "backend.app",
    "backend.app.main",
    "backend.app.licensing",
    "backend.app.hardware.intervalometer",
    "backend.app.hardware.tether",
    "backend.app.pipeline.alignment",
    "backend.app.pipeline.gates",
    "backend.app.pipeline.gradient",
    "backend.app.pipeline.ingest",
    "backend.app.pipeline.satellites",
    "backend.app.pipeline.stacker",
    "backend.app.pipeline.stretch",
]

# Collect all submodules from core packages
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("backend")
hiddenimports += collect_submodules("cryptography")

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AstroLink",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to True for field diagnostics/logs; can be toggled to False for windowless
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
