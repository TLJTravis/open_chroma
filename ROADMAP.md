# OpenChroma Development Roadmap

This document outlines completed milestones, upcoming priorities, and long-term architectural goals for OpenChroma.

---

## Completed Milestones

- [x] **Wayland & X11 Hybrid Compatibility (v1.0.5)**
  - Dual-backend window tracking using `xdotool` on X11/Cinnamon and GNOME Shell DBus on Wayland.
  - Automatic runtime Qt platform abstraction setup (`QT_QPA_PLATFORM="wayland;xcb"`).

- [x] **Pointer-Safe Hardware Input Grabbing (v1.0.5)**
  - Low-level `evdev` device scanning that filters out relative motion (`EV_REL`) devices to prevent cursor freezing while capturing side-plate buttons.

- [x] **Clean Process Shutdown & Device Releasing (v1.0.3 - v1.0.5)**
  - Thread teardown and signal handling ensuring `ungrab()` and virtual `uinput` nodes close cleanly upon exit.

- [x] **System Tray & Profile Management (v1.0.3 - v1.0.5)**
  - System tray icon with quick game profile selection, window toggling, and XDG autostart management.

- [x] **Independent Dual-Device Chroma Control (v1.0.4)**
  - Independent static colors, brightness sliders, and breathing modes for connected Razer mice and keyboards via `razer_backend.py`.

- [x] **Structured Logging & OSD Notifications (v1.0.3)**
  - Replaced silent exceptions with timestamped Python `logging` outputs and added non-focus-stealing DPI OSD popups.

---

## Phase 1: High Priority (Core Reliability & Security)

- [ ] **Installation Integrity (SHA-256 Checksums)**
  - Add SHA-256 checksum generation to release builds.
  - Update `install.sh` to download and verify checksums prior to execution.
  - *Acceptance Criteria:* Installation aborts immediately with an error if checksum verification fails.

- [x] **Input Device Access & Permission Verification**
  - Verify exclusive access rights (`evdev` / OpenRazer daemon / `plugdev` group) prior to binding or remapping inputs.
  - *Acceptance Criteria:* Displays a user-friendly GUI/CLI notification if permissions are missing (e.g., user not in `plugdev` or missing `udev` rules).

- [ ] **Modular Code Restructuring**
  - Refactor single-file monolith into structured submodules (`openchroma/core/`, `openchroma/ui/`, `openchroma/devices/`).
  - *Acceptance Criteria:* Main entry point imports modules cleanly without circular dependencies.

---

## Phase 2: Medium Priority (Packaging & Distribution)

- [ ] **Flatpak & AppImage Packaging**
  - Package OpenChroma for distribution on Flathub and universal AppImage formats with `uinput` permissions rules.

- [x] **Dependency Pinning**
  - Maintain verified Python dependency versions in `requirements.txt` and `pyproject.toml`.

---

## Phase 3: Long-Term & Community Features

- [ ] **Automated Test Suite**
  - Implement unit and integration tests using `pytest` for profile JSON validation, keycode mapping, and device scanning logic.

- [ ] **Community Profile Sharing**
  - Import/Export profile preset templates for popular games directly within the UI.
