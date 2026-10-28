#!/bin/bash

# Exit immediately if any command fails
set -e

echo "=== Installing OpenChroma and System Dependencies ==="

# 1. Install required system and Python dependencies based on package manager
if command -v apt-get &> /dev/null; then
    echo "[+] Installing system dependencies via apt..."
    sudo apt update
    sudo apt install -y python3-pyqt6 python3-evdev python3-dbus python3-xlib xdotool openrazer-meta flatpak python3-pip
elif command -v dnf &> /dev/null; then
    echo "[+] Installing system dependencies via dnf..."
    sudo dnf install -y python3-qt5 python3-evdev xdotool flatpak python3-pip
else
    echo "[!] Unrecognized package manager. Please ensure required dependencies are installed manually."
fi

# Ensure user has access to hardware devices
echo "[+] Adding '$USER' to 'plugdev' group..."
sudo usermod -aG plugdev "$USER" || sudo gpasswd -a "$USER" plugdev || true

# 2. Install Python Pip Dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "[+] Installing Python requirements..."
    pip3 install -r requirements.txt --user
fi

# 3. Setup OpenRGB Flatpak server for per-zone mouse control
echo "[+] Checking OpenRGB Flatpak dependency..."
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true
if ! flatpak list | grep -q "org.openrgb.OpenRGB"; then
    echo "[+] Installing OpenRGB Flatpak..."
    flatpak install -y flathub org.openrgb.OpenRGB
fi

# Apply sandbox device access overrides
echo "[+] Granting OpenRGB sandbox hardware access..."
flatpak override --user --device=all org.openrgb.OpenRGB

# Configure OpenRGB to start automatically as a background server on login
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat << 'EOF' > "$AUTOSTART_DIR/openrgb-server.desktop"
[Desktop Entry]
Type=Application
Name=OpenRGB Server
Exec=flatpak run org.openrgb.OpenRGB --server --no-gui
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Starts OpenRGB SDK server in background for OpenChroma
EOF

# 4. Setup local application directories
SHARE_DIR="$HOME/.local/share/openchroma"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$SHARE_DIR/assets"
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# 5. Copy application files from the current repository workspace
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

# 6. Create a symlink in PATH so users can type 'openchroma' anywhere
ln -sf "$SHARE_DIR/open_chroma_wayland.py" "$INSTALL_DIR/openchroma"

# 7. Install desktop file and icon if available
if [ -f "open_chroma.desktop" ]; then
    cp "open_chroma.desktop" "$DESKTOP_DIR/"
fi

if [ -f "$SHARE_DIR/assets/OpenChroma.png" ]; then
    cp "$SHARE_DIR/assets/OpenChroma.png" "$ICON_DIR/OpenChroma.png"
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true
fi

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# Dynamically update the installed desktop file with absolute paths
if [ -f "$DESKTOP_DIR/open_chroma.desktop" ]; then
    sed -i "s|Exec=open_chroma|Exec=$INSTALL_DIR/openchroma|g" "$DESKTOP_DIR/open_chroma.desktop"
    sed -i "s|Icon=openchroma|Icon=$ICON_DIR/OpenChroma.png|g" "$DESKTOP_DIR/open_chroma.desktop"
fi

# 8. Enable and start daemons
systemctl --user daemon-reload
systemctl --user enable --now openrazer-daemon.service 2>/dev/null || echo "Note: OpenRazer service will be active after logging back in."

# Start the OpenRGB server immediately for this session
flatpak run org.openrgb.OpenRGB --server --no-gui &>/dev/null &

echo "=== Installation complete! OpenChroma is ready to use. ==="
echo "Note: Please log out and back in for group membership (plugdev) and Flatpak overrides to take full effect."