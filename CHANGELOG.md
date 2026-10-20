# Changelog

All notable changes to OpenChroma will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- SHA-256 checksum verification during installation.
- Improved OpenRazer device access validation and hardware detection.
- Clean process signal handling (`SIGINT`/`SIGTERM`).

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
