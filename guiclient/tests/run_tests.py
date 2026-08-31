import os
import sys
from pathlib import Path
import pytest  # Replaces unittest

if __name__ == '__main__':
    # Clear previous messages 
    # \033[2J = clear visible screen
    # \033[3J = clear scrollback buffer (crucial for VS Code)
    # \033[H  = move cursor to top left
    print('\033[2J\033[3J\033[H', end='', flush=True)

    # Disable verbose Qt debug logging output
    os.environ["QT_LOGGING_RULES"] = "*.debug=false"
    
    # --- THE MAGIC HEADLESS FIX ---
    # Force Qt to run in memory without connecting to a display server
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    
    # Calculate the project root (one folder up from this script)
    project_root = Path(__file__).resolve().parent.parent
    
    # Force the Current Working Directory (CWD) to the project root
    os.chdir(project_root)
    
    # Ensure the root is in the Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Run Pytest programmatically
    #exit_code = pytest.main(["-v", "tests"])
    # "-s" disables output capturing (shows all print statements)
    # "-v" is verbose mode (equivalent to unittest verbosity=2)
    # "tests" points to your test directory
    #eg.
    exit_code = pytest.main(["-s", "-v", "tests"])
    
    sys.exit(exit_code)