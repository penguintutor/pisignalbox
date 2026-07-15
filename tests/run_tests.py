import os
import sys
import unittest
from pathlib import Path

if __name__ == '__main__':
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
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests")    
    
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)