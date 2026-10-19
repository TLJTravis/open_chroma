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
