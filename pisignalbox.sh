#!/usr/bin/bash
cd ~/pisignalbox
source ~/venv/pyvlcb/bin/activate

# Check if the server is already running
pid=$(pgrep -f "python3 ./vlcbserver.py")

if [ -n "$pid" ]; then
    echo "Server already running PID $pid. Skipping startup."
else
    echo "Starting vlcbserver..."
    ./vlcbserver.py &
    # Give it a brief moment to initialize before checking PID or moving on
    sleep 1
    pid=$(pgrep -f "python3 ./vlcbserver.py")
    echo "Server started with PID $pid"
fi

./app.py

# Show pid of server
pid=$(pgrep -f "python3 ./vlcbserver.py")
if [ -n "$pid" ]; then
    echo "Server still running PID $pid"
else
    echo "Server is not running."
fi
