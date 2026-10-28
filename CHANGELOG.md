# Changelog

All notable changes to OpenChroma will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- SHA-256 checksum verification during installation.
- Clean process signal handling (`SIGINT`/`SIGTERM`).
---

## Keyboard/Mouse editor US/UI upgrades & fixes for bugs in those modules - 2026-10-28

### Added
- **Keyboard Matrix Grid & Paint Canvas:** Implemented per-key 6x22 matrix RGB lighting editor, visual painting canvas, color gamut color picker, and real-time hardware flushing.
- **Mouse Zone Customization UI & Backend:** Added interactive mouse zone selection (Scroll Wheel, Logo, Keypad) and guarded `set_mouse_zone` handling in `RazerBackend` to safely interface with OpenRazer mouse features while preventing `NoneType` crashes.
- **OpenRGB Background Daemon Integration:** Integrated OpenRGB Flatpak installation and automatic autostart configuration (`openrgb-server.desktop`) into `install.sh` to handle low-level USB communication over SDK port 6742.

### Fixed
- **Keyboard Matrix Persistence:** Fixed profile saving logic so clicking "Clear All" and saving cleanly flushes empty matrix data from JSON profiles instead of retaining prior color states.
- **Editor Initialization:** Resolved initial launch state so the editor starts up clean without pre-selecting or prematurely highlighting keys.
- **Mouse Logo Highlight Alignment:** Adjusted `MouseZoneWidget` Y-coordinate positioning (fine-tuned to `85`) to ensure the interactive highlight box aligns cleanly over the Naga Trinity logo graphic.
---
## Keyboard Matrix & Mouse Lighting(basic)m Fixed Editor memory &initialization - 2026-10-27

### Added
- **Keyboard Matrix Grid & Paint Canvas:** Implemented per-key 6x22 matrix RGB lighting editor, visual painting canvas, color gamut color picker, and real-time hardware flushing.
- **Mouse Zone Customization UI & Backend:** Added interactive mouse zone selection (Scroll Wheel, Logo, Keypad) and guarded `set_mouse_zone` handling in `RazerBackend` to safely interface with OpenRazer mouse features while preventing `NoneType` crashes.

### Fixed
- **Keyboard Matrix Persistence:** Fixed profile saving logic so clicking "Clear All" and saving cleanly flushes empty matrix data from JSON profiles instead of retaining prior color states.
- **Editor Initialization:** Resolved initial launch state so the editor starts up clean without pre-selecting or prematurely highlighting keys.
---

## [1.0.6] - Debian Packaging Fixes & Path Resolution - 2026-10-25

### Fixed
- **Debian Packaging (`debian/control`)**: Corrected package dependencies and build configurations to ensure smooth installation via `.deb` packages.
- **Module Paths & Symlinks**: Fixed binary symlinks and module resolution paths so OpenChroma executes reliably from system paths.
- **Hardware Detection**: Verified proper udev rules and user permission mappings for seamless Razer peripheral detection across both X11 and Wayland sessions.

---

## [1.0.5] - Wayland/X11 Hybrid Support & Pointer Freedom - 2026-10-24

### Added
- **Hybrid X11 & Wayland Display Engine**: Automatic runtime environment detection fallback using `QT_QPA_PLATFORM="wayland;xcb"`.
- **Cross-Platform Auto-Profile Switcher**: Dual-backend window tracking incorporating `xdotool` for X11/Cinnamon (Linux Mint) and GNOME Shell DBus for Wayland (Ubuntu).
- **Universal Hardware Peripheral Scanner**: Dynamic detection and support for any connected Razer mouse or keyboard via OpenRazer and `evdev`.
- **XDG Autostart Integration**: Desktop autostart toggle within UI settings with automatic `.desktop` file creation and removal.
- **System Tray Management**: System tray icon with quick game profile switching and window visibility controls.

### Fixed
- **System Cursor Freeze**: Isolated input grabbing logic specifically to keypad/macro nodes, excluding relative motion (`EV_REL`) devices to preserve system pointer movement.
- **X11 Display Scaling**: Prevented interface clipping on various desktop environments and display configurations.
- **Python Bytecode Cache Invalidation**: Ensured reliable module loading during cross-machine deployments.

---
## [1.0.4] - Dual-Peripheral Header & Custom Device Icons - 2026-10-22
### Added
- **Dual-Peripheral Header Layout:** Refactored top device info card into a dedicated dual-icon and dual-label system (`keyboard_icon_lbl`, `keyboard_lbl`, `mouse_icon_lbl`, `mouse_lbl`) to independently present status and thumbnails for connected devices.
- **Distinct Device Fallback Assets:** Integrated custom fallback asset support (`keyboard_default.png` and `mouse_default.png`) to render tailored gaming-themed graphics when remote hardware images are unavailable.
- **Core Backend Module Integration:** Formally tracked and packaged `razer_backend.py` as a core dependency for direct OpenRazer device communication and lighting control.

### Changed
- **Independent Hardware Label Updates:** Updated `update_detected_hardware_labels` to independently fetch, smooth-scale, and render distinct icon pixmaps alongside text descriptions for both peripherals.

### Fixed
- **Robust Image Caching & Size Validation:** Enhanced `get_cached_device_image` with a dynamic `fallback` parameter and automatic size-validation cleanup to discard invalid or 404 error stubs (< 100 bytes) from `~/.cache/openchroma/images/`.
- **Network Error Resolution:** Prevented HTTP 404 exceptions by gracefully falling back to local project assets (`assets/`) when remote GitHub data paths fail or are omitted.
---
## [1.0.3] - Window Geometry, Asset Path Resolution, UX/UI Changes - 2026-10-20
### Added
- Window geometry tracking: OpenChroma now remembers and retains its exact screen position and monitor when minimized and restored from the system tray.
- Profile deletion confirmation: Added a safety prompt dialog to prevent accidental deletion of custom configuration profiles.
- Startup configuration option: Added a direct checkbox toggle in the main interface to automatically launch OpenChroma on system startup.
- System tray management: Integrated full tray icon support with quick actions to show the app, switch profiles, and quit cleanly.
- DPI preset stage snapping: Smoothly snaps slider adjustments to the closest hardware DPI preset stage with an OSD notification.
- Independent per-device Chroma lighting controls, allowing separate customization for mouse and keyboard effect modes, brightness, and breathing ranges.

### Fixed
- Fixed asset path resolution when installed or run outside the primary source folder, ensuring the tray icon (`OpenChroma.png`) and GUI elements load reliably across all environments.
- Updated `install.sh` to package the full application bundle and assets into a dedicated share directory with proper symlink resolution.

---
## Medium Code Fixes and Syntax Corrections - 10/19/2026

### Fixed
* **Hardware Event Node Binding:** Resolved issue where device detection selected generic mouse pointer endpoints by prioritizing `/dev/input/event9` with dynamic capability verification fallback.
* **Keycode Offset Correction:** Switched from `evdev.ecodes` constants to raw integer keycode mapping (`2`–`13`) in `trinity_map` to accurately align with Naga Trinity side-plate matrix events.
* **Macro Processor Crash:** Restored missing `sanitize_action` method in `LiveInputDaemon` to eliminate `AttributeError` exceptions when parsing key combinations and modifier sequences.

### Changed
* **Terminal Output Optimization:** Commented out verbose raw `evdev` event debug printing in the primary input loop for clean production logging.

---
## [1.0.1] - Minor bug Fixes and Window Switching - 10/18/2026
### Added
A quick summary of what we completed today:

- Author Line: Updated header branding to TLJTravis.
- Code Organization: Applied 9 standard visual section comment blocks across all 1,617 lines.
- Lifecycle Handling: Renamed entry block to Application Entry/Exit Point to accurately reflect
    startup and thread teardown   (sys.exit).
- Auto-Profile Fix: Standardized window title matching so FFXIV / "FINAL FANTASY XIV" auto-switches cleanly out-of-the-box.

---
## [1.0.0] - Initial Release: 10/17/2026

### Added
- Core OpenRazer integration for mouse lighting and button customization.
- One-command terminal installation script (`install.sh`) via `curl`.
- Desktop integration (`.desktop` entry and application icon).
- OpenRazer attribution in documentation and repository metadata.
