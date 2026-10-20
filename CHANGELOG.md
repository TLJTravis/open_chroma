# Changelog

All notable changes to OpenChroma will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
Wayland compositor integrations is currently NOT planned. Feel free to fork this program if you wish for it to work on Wayland

### Planned
- SHA-256 checksum verification during installation.
- Improved OpenRazer device access validation and hardware detection.
- Clean process signal handling (`SIGINT`/`SIGTERM`).

---
## [1.0.3] - Window Geometry, Asset Path Resolution, UX/UI Changes 2026-10-20
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
## [1.0.1] - Minor bug Fixes and Window Switching 10/18/2026
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
