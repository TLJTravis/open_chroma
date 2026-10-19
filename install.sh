#!/bin/bash

# Exit immediately if any command fails
set -e

echo "Fetching the latest release of OpenChroma..."

REPO="TLJTravis/open_chroma"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Get direct download URLs for the binary and its checksum file
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep "browser_download_url" | grep -v "\.sha256" | cut -d '"' -f 4 | head -n 1)
CHECKSUM_URL=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep "browser_download_url" | grep "\.sha256" | cut -d '"' -f 4 | head -n 1)

if [ -z "$DOWNLOAD_URL" ] || [ -z "$CHECKSUM_URL" ]; then
    echo "Error: Could not find the release binary or checksum file."
    exit 1
fi

echo "Downloading OpenChroma and verification checksum..."
curl -L -o "$INSTALL_DIR/open_chroma" "$DOWNLOAD_URL"
curl -L -o "$INSTALL_DIR/open_chroma.sha256" "$CHECKSUM_URL"

# Verify the checksum
echo "Verifying file integrity..."
cd "$INSTALL_DIR"
if ! sha256sum -c open_chroma.sha256 --status; then
    echo "Error: Checksum verification failed! The downloaded file may be corrupted."
    rm -f open_chroma open_chroma.sha256
    exit 1
fi

# Clean up the checksum file and set executable permissions
rm -f open_chroma.sha256
chmod +x "$INSTALL_DIR/open_chroma"

# Install desktop file if present locally
if [ -f "open_chroma.desktop" ]; then
    cp open_chroma.desktop "$DESKTOP_DIR/"
fi

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "Installation complete and verified! OpenChroma is ready to use."
