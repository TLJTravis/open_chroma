# OpenChroma

OpenChroma is a lightweight, universal control utility designed for Linux. It provides per-profile key remapping, automated window profile switching, and customizable Chroma lighting management for Razer peripherals (such as the Razer Naga Trinity and Ornata V2) on Linux distributions like Linux Mint.

## Acknowledgments
- This project utilizes code and concepts from [OpenRazer](https://github.com/openrazer/openrazer) for device communication and driver management.
---

## Features

- **Automated Profile Switching:** Automatically detects active game windows (configured for FFXIV, PSO2 NGS, and more) and swaps keybind/DPI profiles using `xdotool`.
- **Side-Keypad & Macro Re-binding:** Safe evdev-based input daemon capturing hardware side buttons and supporting modifier-only holds (`Ctrl`, `Shift`, `Alt`).
- **Per-Profile DPI Control & OSD:** Independent DPI stages with a non-focus-stealing OSD notification popup.
- **Independent Lighting Controls:** Adjust static colors via a 16M gamut spectrum picker, custom hex codes, or breathing effect modes for mouse and keyboard.



## Prerequisites & Dependencies

OpenChroma relies on Python 3, PyQt6, `python-evdev`, `python-xlib`, and `xdotool`. 

Make sure `xdotool` is installed on your system:
```bash
sudo apt install xdotool   # Debian / Ubuntu / Linux Mint
sudo dnf install xdotool   # Fedora

---

## Installation

You can install OpenChroma with a single command using `curl`:

```bash
curl -sSL [https://raw.githubusercontent.com/TLJTravis/open_chroma/main/install.sh](https://raw.githubusercontent.com/TLJTravis/open_chroma/main/install.sh) | bash
