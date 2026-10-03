# AstroLink — Autonomous Field Stacking & EAA Field Station

[![CI/CD](https://github.com/achala500/astrolink/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/achala500/astrolink/actions/workflows/ci-cd.yml)
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
├── docker-compose.yml      # Local Docker Compose for development
├── render.yaml             # Render.com free web service blueprint
├── fly.toml                # Fly.io deployment configuration
├── railway.json            # Railway.app deployment configuration
├── koyeb.yaml              # Koyeb free tier deployment
├── Procfile                # Heroku-style process declaration
├── .github/workflows/      # Automated CI/CD, multi-platform binaries & GHCR Docker publish
├── example_license.key     # Pre-signed valid offline lifetime license key
└── requirements.txt        # Pinned Python dependencies
```

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/achala500/astrolink.git
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

The signing private key is intentionally **not shipped in the repository or application**. Run the minting command only on a secure licensing workstation:

```bash
export ASTROLINK_LICENSE_MINT_PRIVATE_KEY="<32-byte-ed25519-seed-in-hex>"
python -m backend.app.licensing mint "Dr. Elena Vance" "lifetime"
unset ASTROLINK_LICENSE_MINT_PRIVATE_KEY

# Verify a license string offline on any installation
python -m backend.app.licensing verify "<base64-license-key>"
```

Never put `ASTROLINK_LICENSE_MINT_PRIVATE_KEY` in Docker, Render, Railway, Fly.io, browser JavaScript, or a public CI log. The application only contains the verification public key.

---

## Multi-Cloud Hosting and Field-Station Architecture

AstroLink has two deliberately different operating modes:

- **Field station mode (recommended for real cameras):** run the service on the laptop/Raspberry Pi connected to the camera. USB tethering, gphoto2, mDNS, and the local intervalometer stay on the same network as the hardware.
- **Cloud demo mode:** deploy the container for remote viewing, uploads, pipeline testing, licensing, and team sharing. Cloud providers cannot access a DSLR connected to your home or observatory, so camera control remains disabled unless the camera is physically attached to that cloud machine.

The Docker image is provider-portable: it listens on the injected `PORT` value (falling back to `8080`) and exposes `/api/status` as a health check. AstroLink can be deployed on **6 cloud platforms** for remote EAA demonstrations and team sharing:

| Platform | Free Tier | Deploy Method | Config File |
|---|---|---|---|
| **Render.com** | 750 hrs/month | Auto-deploy from GitHub | `render.yaml` |
| **Fly.io** | 3 shared VMs | CLI `fly deploy` | `fly.toml` |
| **Railway.app** | \$5 credit/month | Connect GitHub repo | `railway.json` |
| **Koyeb** | 1 free nano instance | Connect GitHub repo | `koyeb.yaml` |
| **Hugging Face Spaces** | 16GB RAM + 2 vCPUs | Push as Docker Space | `Dockerfile` |
| **GitHub Container Registry** | Public image hosting | Auto-published via CI/CD | `.github/workflows/ci-cd.yml` |

> Free plans and quotas change frequently. Treat Render/Koyeb/Fly as demo targets and do not rely on an ephemeral instance for irreplaceable astrophotography data. The live stack is intentionally in memory; export the TIFF after a session.

### Deploy the portable container

Build and smoke-test locally first:

```bash
docker build -t astrolink:local .
docker run --rm -p 8080:8080 -e PORT=8080 astrolink:local
curl http://localhost:8080/api/status
```

Every provider should wait for `GET /api/status` to return `200` before routing traffic. For a cloud deployment, use a private license key through `ASTROLINK_LICENSE`; never commit a generated license key or camera credentials.

For public deployments, configure the feedback administration token:

```bash
ASTROLINK_ADMIN_TOKEN="use-a-long-random-secret"
```

When configured, send `Authorization: Bearer <token>` to feedback listing, exports, status updates, clearing, and attachment download endpoints. Feedback submission remains available to end users. Without this token, those administrative endpoints are intentionally open for local/offline installations only; do not expose that mode publicly.

For a private cloud API, also set `ASTROLINK_API_TOKEN`. This protects frame upload, export, reset, camera detection/status, license activation/deactivation, and WebSocket commands. Build the frontend with the matching `VITE_ASTROLINK_API_TOKEN`; it will attach the token to API requests and the WebSocket connection. Do not use this mode for a public multi-user application because browser users can inspect any token embedded in their frontend bundle.

To preserve a stack across a restart, mount persistent storage and set:

```bash
ASTROLINK_SESSION_FILE=/data/astrolink-session.npz
```

Without a persistent volume, a cloud restart intentionally clears the in-memory stack.

### Option A: Render.com (Recommended — Zero Config)
1. Go to [render.com/new](https://render.com/new) → **New Web Service**.
2. Connect your GitHub repository: `achala500/astrolink`.
3. Render automatically detects `render.yaml` and builds the multi-stage Docker container.
4. Live URL: `https://astrolink-field-station.onrender.com`

### Option B: Fly.io
```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly launch --config fly.toml
fly deploy
```

### Option C: Railway.app
1. Go to [railway.app/new](https://railway.app/new) → **Deploy from GitHub Repo**.
2. Select `achala500/astrolink`.
3. Railway detects `railway.json` and `Dockerfile` automatically.

### Option D: Koyeb
1. Go to [app.koyeb.com](https://app.koyeb.com) → **Create App** → **GitHub**.
2. Select `achala500/astrolink`, Koyeb builds from `Dockerfile`.

### Option E: Hugging Face Spaces (Best for Science Demos)
1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces).
2. Select **Docker** as the SDK.
3. Push this repo — Hugging Face will build the `Dockerfile` and host it with generous RAM for scientific stacking.

### Option F: Docker (Self-Hosted / Any Cloud)
```bash
# Pull pre-built image from GitHub Container Registry
docker pull ghcr.io/achala500/astrolink:latest
docker run -p 8080:8080 ghcr.io/achala500/astrolink:latest

# Or build & run locally with Docker Compose
docker-compose up --build
```

---

## GitHub Repository

**Repository**: [github.com/achala500/astrolink](https://github.com/achala500/astrolink)

The included [GitHub Actions workflow](.github/workflows/ci-cd.yml) automatically:
- ✅ Runs the full 20-test suite on every push
- 📦 Builds Windows & Linux desktop binaries
- 🐳 Publishes Docker images to GitHub Container Registry (GHCR)
- 🚀 Creates GitHub Releases with binaries on version tags (`v*`)

---

## License

MIT License. Designed with precision for astronomers worldwide.
