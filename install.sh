#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Installing OpenChroma (Wayland Version) and system dependencies..."

# 1. Install required system and Python dependencies via apt
sudo apt update
sudo apt install -y python3-pyqt6 python3-evdev python3-dbus xdotool openrazer-meta

# Ensure user has access to hardware devices
sudo gpasswd -a "$USER" plugdev || true

# 2. Setup local application directories
SHARE_DIR="$HOME/.local/share/openchroma"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$SHARE_DIR/assets"
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# 3. Copy application files from the current repository workspace
if [ -f "open_chroma_wayland.py" ]; then
    cp "open_chroma_wayland.py" "$SHARE_DIR/open_chroma_wayland.py"
    chmod +x "$SHARE_DIR/open_chroma_wayland.py"
else
    echo "Error: open_chroma_wayland.py not found in current directory."
    exit 1
fi

if [ -f "razer_backend.py" ]; then
    cp "razer_backend.py" "$SHARE_DIR/razer_backend.py"
else
    echo "Error: razer_backend.py not found in current directory."
    exit 1
fi

if [ -f "assets/OpenChroma.png" ]; then
    cp "assets/OpenChroma.png" "$SHARE_DIR/assets/OpenChroma.png"
fi

# 4. Create a symlink in PATH so users can type 'openchroma' anywhere
ln -sf "$SHARE_DIR/open_chroma_wayland.py" "$INSTALL_DIR/openchroma"

# 5. Install desktop file and icon if available
if [ -f "open_chroma.desktop" ]; then
    cp "open_chroma.desktop" "$DESKTOP_DIR/"
fi

if [ -f "$SHARE_DIR/assets/OpenChroma.png" ]; then
    cp "$SHARE_DIR/assets/OpenChroma.png" "$ICON_DIR/OpenChroma.png"
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true
fi

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# Dynamically update the installed desktop file with absolute paths
if [ -f "$DESKTOP_DIR/openchroma.desktop" ]; then
    sed -i "s|Exec=open_chroma|Exec=$INSTALL_DIR/openchroma|g" "$DESKTOP_DIR/openchroma.desktop"
    sed -i "s|Icon=openchroma|Icon=$ICON_DIR/OpenChroma.png|g" "$DESKTOP_DIR/openchroma.desktop"
fi

# 6. Enable and start the OpenRazer daemon user service
systemctl --user daemon-reload
systemctl --user enable --now openrazer-daemon.service || echo "Note: OpenRazer service will be active after logging back in."

echo "Installation complete! OpenChroma is ready to use."
