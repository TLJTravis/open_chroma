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
- **Per-Profile DPI Control & OSD**: Independent DPI stages with snap-to-preset sliders and a non-focus-stealing OSD notification overlay.
- **Independent Chroma Lighting Controls**: Custom static colors via a 16M gamut picker, hex codes, brightness scaling, and breathing effect modes per device.
- **System Tray & Autostart Management**: Full tray icon integration with quick profile switching and an XDG desktop autostart configuration toggle.

---

## Prerequisites & Dependencies

OpenChroma requires Python 3, PyQt6, `python-evdev`, and `openrazer`.

### System Packages

**Ubuntu / Debian / Linux Mint:**
```bash
sudo apt update
sudo apt install python3-pyqt6 python3-evdev python3-dbus xdotool
```

**Fedora:**
```bash
sudo dnf install python3-qt5 python3-evdev xdotool
```

### OpenRazer & User Permissions
Ensure `openrazer-daemon` is installed and your account belongs to the `plugdev` group:
```bash
sudo usermod -aG plugdev $USER
```
*(Re-log into your system session for group permissions to take effect).*

---

## Installation

You can install OpenChroma with a single command using `curl`:

```bash
curl -sSL https://raw.githubusercontent.com/TLJTravis/open_chroma/main/install.sh | bash
```

Alternatively, clone and launch directly:
```bash
git clone https://github.com/TLJTravis/open_chroma.git
cd open_chroma
python3 open_chroma_wayland.py
```

---

## Configuration & Profiles

Profile mappings, DPI settings, and aliases are saved in JSON format at:
```text
~/.config/naga_profiles.json
```
Profiles can also be exported and imported directly through the GUI **Customize** tab.

---

## License

Distributed under the MIT License.