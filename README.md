# OpenChroma

OpenChroma is a lightweight, universal control utility designed for Linux. It brings full Synapse-style feature parity—including per-profile key remapping, dynamic window auto-profile switching, sensitivity staging, and custom Chroma RGB lighting management—to Razer peripherals across both **Wayland** and **X11** desktop environments.

## Acknowledgments
- This project utilizes code and concepts from [OpenRazer](https://github.com/openrazer/openrazer) for device communication and driver management.

---

## Features

- **Hybrid X11 & Wayland Support**: Native compatibility across X11 (Linux Mint / Cinnamon, XFCE, KDE) and Wayland (Ubuntu / GNOME) with automatic runtime fallback (`QT_QPA_PLATFORM="wayland;xcb"`).
- **Multi-Backend Auto-Profile Switching**: Dynamically switches keybind, macro, and DPI profiles by tracking active windows via `xdotool` on X11 or GNOME Shell DBus on Wayland.
- **Pointer-Safe Keypad Remapping**: Low-level `evdev` & `uinput` input daemon that isolates keypad/side-plate macro nodes without grabbing or freezing relative mouse motion (`EV_REL`).
- **Universal Peripheral Scanner**: Dynamic detection and support for connected Razer mice (e.g., Naga Trinity) and keyboards (e.g., Ornata V2) using OpenRazer driver endpoints.
- **Advanced Per-Key & Per-Zone Chroma Editors**: 
  - **Keyboard Matrix Grid & Paint Canvas:** Per-key 6x22 matrix RGB lighting editor with visual painting canvas and gamut color picker.
  - **Mouse Zone Customization:** Independent multi-zone RGB control (Scroll Wheel, Logo, Keypad) powered by a local OpenRGB Flatpak background server (`127.0.0.1:6742`) for direct-mode hardware rendering.
- **Per-Profile DPI Control & OSD**: Independent DPI stages with snap-to-preset sliders and a non-focus-stealing OSD notification overlay.
- **System Tray & Autostart Management**: Full tray icon integration with quick profile switching and an XDG desktop autostart configuration toggle.

---

## Prerequisites & Dependencies

OpenChroma requires Python 3, PyQt6, `python-evdev`, `openrazer`, `flatpak`, and `OpenRGB`.

### System Packages

**Ubuntu / Debian / Linux Mint:**
```bash
sudo apt update
sudo apt install python3-pyqt6 python3-evdev python3-dbus xdotool openrazer-meta flatpak
```
Fedora:

```Bash
sudo dnf install python3-qt5 python3-evdev xdotool flatpak
```
OpenRGB Setup & Device Permissions
OpenChroma uses OpenRGB operating as a background SDK daemon (listening on 127.0.0.1:6742) to handle low-level per-zone RGB control for complex peripherals like the Razer Naga Trinity.

To set up the OpenRGB backend daemon:

1. Install OpenRGB via Flatpak
Add the Flathub repository (if not already present) and install the OpenRGB Flatpak package:

```Bash
flatpak remote-add --if-not-exists flathub [https://dl.flathub.org/repo/flathub.flatpakrepo](https://dl.flathub.org/repo/flathub.flatpakrepo)
flatpak install flathub org.openrgb.OpenRGB
```
2. Configure Hardware Access & Sandbox Overrides
Flatpak applications run in an isolated sandbox by default. Grant OpenRGB permission to access your USB hardware directly:

```Bash
flatpak override --user --device=all org.openrgb.OpenRGB
```
Ensure your user account belongs to the plugdev group for OpenRazer and USB device access:

```Bash
sudo usermod -aG plugdev $USER
```
(Log out and log back into your desktop session for group permissions and Flatpak overrides to take effect).

3. Start the Background Daemon
Run OpenRGB as a headless SDK server in the background:

```Bash
flatpak run org.openrgb.OpenRGB --server --no-gui
```
(Note: install.sh configures an autostart desktop entry so this daemon starts automatically upon login).

Installation
You can install OpenChroma with a single command using curl:

```Bash
curl -sSL [https://raw.githubusercontent.com/TLJTravis/open_chroma/main/install.sh](https://raw.githubusercontent.com/TLJTravis/open_chroma/main/install.sh) | bash
```
Alternatively, clone and launch directly:

```Bash
git clone [https://github.com/TLJTravis/open_chroma.git](https://github.com/TLJTravis/open_chroma.git)
cd open_chroma
python3 open_chroma_wayland.py
```
Configuration & Profiles
Profile mappings, DPI settings, and aliases are saved in JSON format at:

Plaintext
~/.config/naga_profiles.json
Profiles can also be exported and imported directly through the GUI Customize tab.

License
Distributed under the MIT License.
