#!/bin/bash

# Get the directory where Pi SignalBox is installed
INSTALL_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)
CURRENT_USER=$(whoami)

echo "Setting up Pi SignalBox for user: $CURRENT_USER at $INSTALL_DIR"

# Setup the GUI Autostart (User level - no sudo required)
mkdir -p ~/.config/autostart
# We generate the desktop file dynamically
cat <<EOF > ~/.config/autostart/pisignalbox-gui.desktop
[Desktop Entry]
Type=Application
Name=Pi SignalBox
Exec=$INSTALL_DIR/pisignalbox.sh
Terminal=false
EOF
echo "GUI autostart installed to ~/.config/autostart/"

# Setup the systemd Server (System level - requires sudo)
echo "Installing systemd service (requires sudo)..."
sudo bash -c "cat <<EOF > /etc/systemd/system/pisignalbox.service
[Unit]
Description=Pi SignalBox VLCB Server
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$HOME/venv/pisignalbox/bin/python3 $INSTALL_DIR/vlcbserver.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
echo "systemd service installed! To enable it to start on boot, run:"
echo "sudo systemctl enable pisignalbox.service"