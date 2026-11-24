# OpenChroma

OpenChroma is a lightweight, universal control utility designed for Linux. It brings Synapse-style feature parity—including per-profile key remapping, dynamic window auto-profile switching, sensitivity staging, and custom Chroma RGB lighting management—to Razer peripherals across both **Wayland** and **X11** desktop environments.

## Acknowledgments
- This project utilizes code and concepts from [OpenRazer](https://github.com/openrazer/openrazer) for device communication and driver management.

---

## Features

- **Hybrid X11 & Wayland Support**: Native compatibility across X11 (Linux Mint / Cinnamon, XFCE, KDE) and Wayland (Ubuntu / GNOME) with automatic runtime fallback (`QT_QPA_PLATFORM="wayland;xcb"`).
- **Multi-Backend Auto-Profile Switching**: Dynamically switches keybind, macro, and DPI profiles by tracking active windows via `xdotool` on X11 or GNOME Shell DBus on Wayland.
- **Kernel `udev hwdb` Keypad Remapping**: Applies per-profile Razer Naga Trinity side-button mappings via `udev` `hwdb` without exclusive `evdev` grabbing or `/dev/uinput` virtual devices.
- **Universal Peripheral Scanner**: Dynamic detection and support for connected Razer mice (e.g., Naga Trinity) and keyboards (e.g., Ornata V2) using OpenRazer driver endpoints.
- **Advanced Per-Key & Per-Zone Chroma Editors**:
  - **Keyboard Matrix Grid & Paint Canvas:** Per-key 6x22 matrix RGB lighting editor with visual painting canvas and gamut color picker.
  - **Mouse Zone Customization:** Independent multi-zone RGB control (Scroll Wheel, Logo, Keypad) powered by a local OpenRGB SDK server (`127.0.0.1:6742`) with immediate zone painting and flushing.
- **Universal Delayed Game RGB Shutdown**: Automatically stops the OpenRGB backend after a game window stays open for ~9 seconds once lighting is applied, letting launch, menu, and server/character-select screens finish first.
- **Per-Profile DPI Control & OSD**: Independent DPI stages with snap-to-preset sliders and a non-focus-stealing OSD notification overlay.
- **System Tray, Profile Renaming & Autostart**: Full tray icon integration with quick profile switching, profile renaming, and an XDG desktop autostart configuration toggle.

---

## Prerequisites & Dependencies

OpenChroma requires Python 3, PyQt6, `openrgb-python`, `openrazer`, `flatpak`, and `OpenRGB`.

### System Packages

**Ubuntu / Debian / Linux Mint:**
```bash
sudo apt update
sudo apt install -y python3-pyqt6 python3-evdev python3-dbus python3-xlib xdotool openrazer-meta flatpak python3-pip desktop-file-utils libglib2.0-bin
