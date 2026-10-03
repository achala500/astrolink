# ==============================================================================
# Stage 1: Build Frontend (Vite + React 18 + Tailwind CSS)
# ==============================================================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Production Python Runtime Environment
# ==============================================================================
FROM python:3.13-slim-bookworm

WORKDIR /app

# Set non-interactive debian frontend & UTF-8 encoding
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Install required system shared libraries for OpenCV, LibRaw, and camera tethering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libgphoto2-6 \
    libraw20 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/
COPY desktop_launcher.py ./

# Copy pre-built React frontend assets from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Most providers inject PORT at runtime (Render/Railway/Koyeb/Cloud Run).
# 8080 remains the local and Fly.io default.
EXPOSE 8080

# Health check endpoint. The shell form lets hosted platforms override PORT.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8080}/api/status" || exit 1'

# Launch Uvicorn on the provider-assigned port and bind externally.
CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
