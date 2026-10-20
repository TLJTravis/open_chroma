#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Fetching the latest release of OpenChroma..."

REPO="TLJTravis/open_chroma"
SHARE_DIR="$HOME/.local/share/openchroma"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$SHARE_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Get direct download URLs
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep "browser_download_url" | grep -v "\.sha256" | cut -d '"' -f 4 | head -n 1)
CHECKSUM_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep "browser_download_url" | grep "\.sha256" | cut -d '"' -f 4 | head -n 1)

if [ -z "$DOWNLOAD_URL" ] || [ -z "$CHECKSUM_URL" ]; then
    echo "Error: Could not find the release binary or checksum file."
    exit 1
fi

echo "Downloading OpenChroma and verification checksum..."
curl -L -o "$SHARE_DIR/open_chroma.py" "$DOWNLOAD_URL"
curl -L -o "$SHARE_DIR/open_chroma.sha256" "$CHECKSUM_URL"

# Verify the checksum
echo "Verifying file integrity..."
cd "$SHARE_DIR"
if ! sha256sum -c open_chroma.sha256 --status; then
    echo "Error: Checksum verification failed! The downloaded file may be corrupted."
    rm -f open_chroma.py open_chroma.sha256
    exit 1
fi

# Clean up checksum and set permissions
rm -f open_chroma.sha256
chmod +x "$SHARE_DIR/open_chroma.py"

# Ensure assets folder exists alongside the script in the share directory
mkdir -p "$SHARE_DIR/assets"
if [ -f "assets/OpenChroma.png" ]; then
    cp assets/OpenChroma.png "$SHARE_DIR/assets/OpenChroma.png"
fi

# Create a symlink in PATH so users can type 'openchroma' anywhere
ln -sf "$SHARE_DIR/open_chroma.py" "$INSTALL_DIR/openchroma"

# Install desktop file and system tray icon if available
if [ -f "open_chroma.desktop" ]; then
    cp open_chroma.desktop "$DESKTOP_DIR/"
fi

if [ -f "$SHARE_DIR/assets/OpenChroma.png" ]; then
    cp "$SHARE_DIR/assets/OpenChroma.png" "$ICON_DIR/OpenChroma.png"
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor/" 2>/dev/null || true
fi

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "Installation complete and verified! OpenChroma is ready to use."
