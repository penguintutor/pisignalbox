#!/usr/bin/bash
# ---------------------------------------------------------
# User Configuration
# If you installed the virtual environment in a different 
# location, update the path below, or use your own startup scripts
# ---------------------------------------------------------
VENV_PATH="$HOME/venv/pisignalbox"

# Activate the virtual environment if it exists
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Warning: Virtual environment not found at $VENV_PATH"
    echo "Attempting to run with system Python..."
fi

# Get the exact directory this bash script lives in
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Launch the Python orchestrator
# The "$@" ensures that any arguments passed to this bash script 
# (like --mock or --data_dir) are passed straight through to Python!
python3 "$SCRIPT_DIR/vlcbserver.py" "$@"



