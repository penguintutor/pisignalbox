import os
import sys
from pathlib import Path
import pytest

if __name__ == '__main__':
    # Clear previous messages 
    # \033[2J = clear visible screen
    # \033[3J = clear scrollback buffer (crucial for VS Code)
    # \033[H  = move cursor to top left
    print('\033[2J\033[3J\033[H', end='', flush=True)

    # Calculate the project root (pisignalbox)
    # .parent = tests/
    # .parent.parent = vlcbserver/
    # .parent.parent.parent = pisignalbox/ (The root where imports work from)
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Force the Current Working Directory (CWD) to the project root
    os.chdir(project_root)
    
    # Ensure the root is in the Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Optional: Set environment variables specifically for your Flask tests
    os.environ["FLASK_ENV"] = "testing"
    # Suppress verbose Werkzeug startup logs during testing if desired
    os.environ["WERKZEUG_RUN_MAIN"] = "true"
    
    # Run Pytest programmatically
    # "-s" disables output capturing (shows all print statements)
    # "-v" is verbose mode
    # "vlcbserver/tests" points to your test directory relative to the new CWD
    exit_code = pytest.main(["-s", "-v", "vlcbserver/tests"])
    
    sys.exit(exit_code)