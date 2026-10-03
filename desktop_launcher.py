"""AstroLink Desktop Launcher.

Starts the embedded FastAPI + WebSocket server in a background worker
and automatically opens the user's default browser to http://localhost:8080.
Used as the main execution entrypoint for PyInstaller single-executable bundles.
"""

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("astrolink.launcher")


def wait_for_server_and_open_browser(url: str = "http://localhost:8080", timeout: float = 12.0) -> None:
    """Polls local socket until server accepts connections, then launches browser."""
    start_time = time.time()
    logger.info("Awaiting AstroLink server initialization...")
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("127.0.0.1", 8080), timeout=0.4):
                time.sleep(0.4)
                logger.info("Server verified active. Opening %s in default browser...", url)
                webbrowser.open(url)
                return
        except (OSError, ConnectionRefusedError):
            time.sleep(0.2)

    logger.warning("Server startup timeout elapsed; attempting browser launch anyway.")
    webbrowser.open(url)


def main() -> None:
    """Launches AstroLink desktop application."""
    # Ensure current directory or bundle root is on sys.path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_dir = Path(sys._MEIPASS)
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))
    else:
        root_dir = Path(__file__).resolve().parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

    # Import uvicorn and app
    import uvicorn
    from backend.app.main import app

    # Spawn browser launcher in daemon thread
    browser_thread = threading.Thread(
        target=wait_for_server_and_open_browser,
        kwargs={"url": "http://localhost:8080", "timeout": 12.0},
        daemon=True,
    )
    browser_thread.start()

    # Run Uvicorn server on all interfaces (enabling local + hotspot connections)
    logger.info("Launching AstroLink server on 0.0.0.0:8080 (mDNS: astrolink.local:8080)...")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
