# Launch the App and Server
import sys
import subprocess
import urllib.request
import urllib.error
import time
from pathlib import Path

# Add guiclient to Python's path ---
# This tricks Python into treating the guiclient folder as a root,
# so all existing imports (like `import core`) continue to work
root_dir = Path(__file__).resolve().parent
gui_dir = root_dir / "guiclient"
sys.path.insert(0, str(gui_dir))

# Import the main function from your completely separate GUI file
from guiclient.app import main as launch_gui

SERVER_URL = "http://127.0.0.1:5000"

def is_server_running():
    try:
        urllib.request.urlopen(f"{SERVER_URL}/", timeout=1)
        return True
    except (urllib.error.URLError, ConnectionError):
        return False

def start_server_detached():
    print("Server not found. Starting background server...")
    subprocess.Popen(
        [sys.executable, "vlcbserver.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True 
    )
    time.sleep(1.5)

if __name__ == '__main__':
    # 1. Handle the server check/startup
    if not is_server_running():
        start_server_detached()
    else:
        print("Server is already running. Connecting...")

    # 2. Hand over control to your massive GUI setup
    launch_gui()