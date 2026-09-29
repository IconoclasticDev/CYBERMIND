"""Launch the local FastAPI/React analyst console in the default browser."""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
import uvicorn

if getattr(sys, "frozen", False):
    assets = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    assets = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(assets / "src"))
os.environ.setdefault("CYBERMIND_CHECKPOINT", str(assets / "checkpoints/final_grouped/best.pt"))
os.environ.setdefault("CYBERMIND_WEB_DIST", str(assets / "web/dist"))
os.environ.setdefault("CYBERMIND_DEMOS_DIR", str(assets / "examples/analyst_demo"))
os.environ.setdefault("CYBERMIND_HOME", str(Path.home() / ".cybermind"))
def main():
    from cybermind.analyst.api import app
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    def open_when_ready():
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    webbrowser.open(f"http://127.0.0.1:{port}")
                    return
            except OSError:
                time.sleep(.1)
    if os.environ.get("CYBERMIND_SKIP_BROWSER") != "1":
        threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
if __name__ == "__main__":
    main()

