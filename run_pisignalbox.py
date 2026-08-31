# Launch the App and Server
import sys
import os 
import json
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

# Import the main function from the GUI client file
from guiclient.app import main as launch_gui

def load_server_config():
    """
    Reads server connection details from JSON configuration files.
    'settings.json' overrides 'default-settings.json'.
    """
    data_dir = gui_dir / "data"
    default_file = data_dir / "default-settings.json"
    user_file = data_dir / "settings.json"

    # Fallback default values
    config = {
        "protocol": "http",
        "hostname": "127.0.0.1",
        "port": 5000
    }

    # Load defaults
    if default_file.exists():
        try:
            with open(default_file, 'r') as f:
                defaults = json.load(f)
                if "server" in defaults:
                    config.update(defaults["server"])
        except Exception as e:
            print(f"Warning: Could not read default-settings.json: {e}")

    # Load user settings (Overwriting defaults)
    if user_file.exists():
        try:
            with open(user_file, 'r') as f:
                user_settings = json.load(f)
                if "server" in user_settings:
                    config.update(user_settings["server"])
        except Exception as e:
            print(f"Warning: Could not read settings.json: {e}")

    return config

def is_server_running(url):
    try:
        urllib.request.urlopen(url, timeout=1)
        return True
    except (urllib.error.URLError, ConnectionError):
        return False

def start_server_detached():
    print("Server not found. Starting background server...")

    server_script = root_dir / "start_server.sh"

    print (f"Script {server_script}")

    subprocess.Popen(
        ["/bin/bash", str(server_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True 
    )
    time.sleep(1.5)

if __name__ == '__main__':
    # Get server details
    config = load_server_config()
    # Defaults included, although should be in default even if not in settings.json
    protocol = config.get("protocol", "http")
    hostname = config.get("hostname", "127.0.0.1")
    port = config.get("port", 5000)

    server_url = f"{protocol}://{hostname}:{port}/"

    # Start server ONLY if it is configured for local machine
    # (Checking for 'localhost' as well just in case a user types that instead)
    if hostname in ["127.0.0.1", "localhost"]:
        if not is_server_running(server_url):
            start_server_detached()
        else:
            print(f"Local server is already running at {server_url}. Connecting...")
    else:
        print(f"Configured for remote server at {server_url}. Skipping local server startup.")

    # Hand over control to the GUI
    launch_gui()