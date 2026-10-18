#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Fetching the latest release of OpenChroma..."

# GitHub repository details
REPO="TLJTravis/open_chroma"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

# Create directories if they don't exist
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Get the direct download URL for the latest binary asset from GitHub Releases
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep "browser_download_url" | cut -d '"' -f 4 | head -n 1)

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Error: Could not find a release binary to download."
    exit 1
fi

echo "Downloading OpenChroma from $DOWNLOAD_URL..."
curl -L -o "$INSTALL_DIR/open_chroma" "$DOWNLOAD_URL"

# Set executable permissions on the binary
chmod +x "$INSTALL_DIR/open_chroma"

# Optional: If your repo includes the .desktop file in the release or source, 
# you can download it too, or keep it bundled locally with your install script.
# For now, we assume open_chroma.desktop is in the same directory as the install script:
if [ -f "open_chroma.desktop" ]; then
    cp open_chroma.desktop "$DESKTOP_DIR/"
fi

# Refresh desktop database so the app shows up immediately
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "Installation complete! OpenChroma is now ready to use."
