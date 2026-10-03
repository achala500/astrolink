# AstroLink — Autonomous Field Stacking & EAA Field Station

[![CI/CD](https://github.com/astrolink/astrolink/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/astrolink/astrolink/actions/workflows/ci-cd.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-6.22+-blue.svg)](https://pyinstaller.org)
[![License: Ed25519 Offline](https://img.shields.io/badge/Licensing-Ed25519_Offline-emerald.svg)](backend/app/licensing.py)

**AstroLink** is a zero-latency, wireless astrophotography field stacking and Electronically Assisted Astronomy (EAA) application. Designed for freezing, pitch-black observing conditions, AstroLink combines an Apple-grade, pure `#000000` OLED interface with a computer vision pipeline and hardware camera tethering engine.

---

## Key Highlights

- **Pure `#000000` OLED Astro Red Mode**: Monochromatic crimson (`#ef4444` / `#7f1d1d`) and obsidian themes protecting dark-adapted vision in remote Bortle 1–3 zones.
- **Hardware-Accelerated Viewport**: 60fps pan/pinch-to-zoom canvas, double-tap recentering, and an interactive star targeting reticle with an inset **6x focus loupe** and live circular **FWHM sharpness gauge**.
- **Human-Language Ergonomics**: Replaces math jargon with intuitive field indicators:
  - *"Welford $\sigma$-Clipping"* $\to$ **Clean Starlight** (satellite streaks & cosmic rays rejected in constant <200MB RAM)
  - *"Polynomial 2D Gradient Extraction"* $\to$ **Clear City Glow** (light pollution removal)
  - *"PixInsight Midtone Transfer Function"* $\to$ **Reveal Deep Sky** (non-linear stretch preserving core color saturation)
- **Universal Multi-Format Ingestion**: Decodes DSLR RAWs (`.CR2`, `.CR3`, `.NEF`, `.ARW`, `.RAF`), Apple ProRAW/Linear DNGs, scientific FITS (`.fits`, `.fit`), 16-bit TIFFs, and JPEGs into unified `float32 [0.0, 1.0]` tensors.
- **Captive Portal Bypass**: Returns HTTP 204 across iOS (`/hotspot-detect.html`), Android (`/generate_204`), Google (`/canonical.html`), and Windows (`/ncsi.txt`) to prevent phones from auto-disconnecting in remote offline hotspots.
- **Zero-Config mDNS**: Broadcasts `_http._tcp.local.` as `http://astrolink.local:8080`.
- **Offline Cryptographic Licensing**: 100% offline Ed25519 asymmetric verification with zero network pings.

---

## Architecture Overview

```
peaceful-kepler/
├── backend/
│   ├── app/
│   │   ├── hardware/       # USB tethering daemon & hardware intervalometer
│   │   ├── pipeline/       # Gates (eccentricity/FWHM), satellites, alignment, stacker, gradient, stretch, ingest
│   │   ├── licensing.py    # Offline Ed25519 cryptographic validator (10-frame trial vs unlimited)
│   │   └── main.py         # FastAPI, WebSocket streaming, captive portal bypass, static mounting
│   ├── test_pipeline.py    # 6 pipeline integration tests
│   ├── test_server.py      # 9 server & network tests
│   └── test_licensing.py   # 5 offline licensing tests
├── frontend/
│   ├── src/
│   │   ├── components/     # DynamicIsland, Viewport, Dock, Controls, SessionSheet, ExportSheet, DurationControls
│   │   ├── utils/          # Web Audio API tactile feedback engine
│   │   ├── App.jsx         # WebSocket engine, WakeLock API, GPS capture, OLED theme
│   │   └── index.css       # Apple HIG styling & Tailwind directives
│   └── dist/               # Built static production bundle
├── desktop_launcher.py     # Desktop launcher (starts Uvicorn & opens default browser)
├── astrolink.spec          # PyInstaller single-executable build specification
├── Dockerfile              # Multi-stage container for cloud deployment
├── render.yaml             # Render.com free web service blueprint
├── fly.toml                # Fly.io deployment configuration
├── .github/workflows/      # Automated CI/CD & multi-platform binary releases
├── example_license.key     # Pre-signed valid offline lifetime license key
└── requirements.txt        # Pinned Python dependencies
```

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/<your-username>/astrolink.git
cd astrolink

# Install dependencies
pip install -r requirements.txt

# Run full test suite (20 tests)
python -m pytest backend/ -v

# Start backend server
python -m backend.app.main
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev     # Development server at http://localhost:5173
npm run build   # Production bundle in frontend/dist
```

---

## Desktop Packaging (PyInstaller Single-Executable)

AstroLink includes a production `astrolink.spec` that automatically collects all OpenCV dynamic DLLs, LibRaw C-libraries (via RawPy), SciPy, Astropy tables, and bundles the compiled React `frontend/dist` directly into the binary's `sys._MEIPASS`.

### Build Windows/Linux Standalone Executable

```bash
# 1. Build frontend first
cd frontend && npm run build && cd ..

# 2. Compile standalone binary with PyInstaller
pyinstaller --clean astrolink.spec
```

The resulting executable will be placed in:
- **Windows**: `dist/AstroLink.exe`
- **Linux/macOS**: `dist/AstroLink`

Double-clicking the binary starts the embedded server and automatically opens the user's default browser to `http://localhost:8080`.

---

## Offline Cryptographic Licensing

AstroLink operates **100% offline with zero external network pings**.

- **Community Trial**: Without a license, stacking is capped at **10 frames per session**.
- **Lifetime / Field Pro**: Unlimited stacking frames.

### Activate a License

1. **Via Key File**: Place your `license.key` in the application directory or `~/.astrolink/license.key`. (An `example_license.key` is provided in the repository).
2. **Via Environment Variable**:
   ```bash
   export ASTROLINK_LICENSE="<base64-license-key>"
   ```
3. **Via API**:
   ```bash
   curl -X POST http://localhost:8080/api/license/activate \
        -H "Content-Type: application/json" \
        -d '{"key": "<base64-license-key>"}'
   ```

### Minting New License Keys (CLI)

```bash
# Mint a lifetime license
python -m backend.app.licensing mint "Dr. Elena Vance" "lifetime"

# Verify a license string offline
python -m backend.app.licensing verify "<base64-license-key>"
```

---

## Free Multi-Platform Cloud Hosting

You can deploy AstroLink on multiple free platforms for remote EAA demonstrations:

### Option A: Render.com (Free Web Service)
1. Fork or push this repository to GitHub.
2. Link your repository in [Render.com](https://render.com).
3. Render automatically detects `render.yaml` and builds the multi-stage Docker container.

### Option B: Fly.io (Free Tier)
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch application
fly launch --config fly.toml
fly deploy
```

### Option C: Hugging Face Spaces (Free 16GB RAM + 2 vCPUs)
1. Create a new Space on [Hugging Face](https://huggingface.co/spaces).
2. Select **Docker** as the SDK.
3. Push this repo — Hugging Face will build the `Dockerfile` and host it with generous RAM for scientific stacking.

---

## Pushing to GitHub

To push this codebase to your own GitHub repository:

```bash
# Initialize git and stage files
git init
git add .
git commit -m "feat: complete AstroLink field station with offline licensing, PyInstaller spec, and cloud configs"

# Add your GitHub remote
git remote add origin https://github.com/<your-username>/astrolink.git

# Set main branch and push
git branch -M main
git push -u origin main
```

Once pushed, the included [GitHub Actions workflow](.github/workflows/ci-cd.yml) will automatically run tests and compile desktop binaries for releases.

---

## License

MIT License. Designed with precision for astronomers worldwide.
