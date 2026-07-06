"""
ironyLabs Links Memex — Standalone Runner (No Docker Required)

Usage:
    cd standalone
    pip install -r requirements.txt
    python run.py

Or use the batch file:
    start-standalone.bat

This runs the full application on a single port (default 8098).
SQLite database stored in ./data/links.db
Opens your browser automatically on startup.
"""

import os
import sys
import webbrowser
import threading
from pathlib import Path

# Resolve paths
STANDALONE_DIR = Path(__file__).parent
PROJECT_ROOT = STANDALONE_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
STATIC_DIR = PROJECT_ROOT / "frontend" / "static"
DATA_DIR = STANDALONE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "uploads").mkdir(exist_ok=True)

# Set environment BEFORE importing anything from backend
os.environ.setdefault("ADMIN_PASSWORD", "123456")
os.environ.setdefault("SECRET_KEY", "standalone_dev_key_change_in_production")
os.environ["DB_PATH"] = str(DATA_DIR / "links.db")
os.environ["UPLOADS_DIR"] = str(DATA_DIR / "uploads")
os.environ["STATIC_DIR"] = ""  # We handle static via our wrapper

PORT = int(os.environ.get("PORT", "8098"))
HOST = os.environ.get("HOST", "127.0.0.1")

# Add backend dir to Python path
sys.path.insert(0, str(BACKEND_DIR))


def open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://{HOST}:{PORT}")


def create_app():
    """Create the standalone app that wraps backend + serves static."""
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from starlette.routing import Mount

    # Import the backend app (it reads env vars we set above)
    import main as backend

    # Create wrapper app (no root_path so URLs work at /)
    wrapper = FastAPI(title="ironyLabs Standalone")

    # Mount backend under /api (backend already has root_path="/api")
    wrapper.mount("/api", backend.app)

    # Serve JS files
    wrapper.mount("/js", StaticFiles(directory=str(STATIC_DIR / "js")), name="js")

    # Serve specific HTML pages
    @wrapper.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @wrapper.get("/admin.html")
    async def admin():
        return FileResponse(str(STATIC_DIR / "admin.html"))

    @wrapper.get("/screensaver.html")
    async def screensaver():
        return FileResponse(str(STATIC_DIR / "screensaver.html"))

    return wrapper


app = create_app()

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════╗
║       ironyLabs Memex — Standalone Mode        ║
╠══════════════════════════════════════════════════════╣
║  URL:    http://{HOST}:{PORT:<5}                         ║
║  Admin:  http://{HOST}:{PORT}/admin.html             ║
║  Data:   ./standalone/data/                          ║
║                                                      ║
║  Press Ctrl+C to stop                                ║
╚══════════════════════════════════════════════════════╝
""")

    threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run("run:app", host=HOST, port=PORT, log_level="info")
