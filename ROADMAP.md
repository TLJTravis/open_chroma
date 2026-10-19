# OpenChroma Development Roadmap

This document outlines planned enhancements, priority bug fixes, and long-term architectural goals for OpenChroma.

---

## Phase 1: High Priority (Core Reliability & Security)

- [ ] **Installation Integrity (SHA-256 Checksums)**
  - Add SHA-256 checksum generation to release builds.
  - Update `install.sh` to download and verify checksums before binary execution.
  - *Acceptance Criteria:* Installation aborts immediately with an error message if checksum verification fails.

- [ ] **Input Device Access Verification**
  - Verify exclusive access rights (`evdev` / OpenRazer daemon connection) prior to binding or remapping inputs.
  - *Acceptance Criteria:* App displays a clean, user-friendly error message if device access is denied or busy, without silently attempting remapping.

- [ ] **Hardware Detection Logic**
  - Validate USB vendor/product IDs against supported OpenRazer device lists.
  - *Acceptance Criteria:* Prevent false-positive detections when unsupported mice or standard input peripherals are connected.

- [ ] **Structured Logging & Error Handling**
  - Replace silent exception suppression (`except: pass`) with standard Python `logging` module output (`--debug` flag support).
  - *Acceptance Criteria:* Runtime errors log timestamped diagnostic details to stdout/stderr or log files.

---

## Phase 2: Medium Priority (Stability & Desktop Integration)

- [ ] **Clean Background Process Shutdown**
  - Implement explicit signal handlers (`SIGINT`, `SIGTERM`) to release held input grabs and terminate background threads cleanly.
  - *Acceptance Criteria:* Closing the application cleanly releases device handles and leaves system input states uninterrupted.

- [ ] **Modular Code Restructuring**
  - Separate main application monolith into dedicated modules (`device/`, `input/`, `profiles/`, `ui/`).
  - *Acceptance Criteria:* Main entry point imports cohesive modules without circular dependencies.

- [ ] **Wayland & X11 Compatibility Checking**
  - Detect current display server environment ($XDG_SESSION_TYPE).
  - *Acceptance Criteria:* Gracefully notify user or disable unsupported remapping features under Wayland if X11-only tools are required.

- [ ] **Dependency Pinning**
  - Document tested Python dependency bounds in `requirements.txt` / `pyproject.toml`.

---

## Phase 3: Future Enhancements & Automated Testing

- [ ] **Automated Test Suite**
  - Implement initial unit/integration tests for hardware detection and profile parsing (`pytest`).
- [ ] **Profile Management & UI Polish**
  - Add quick profile switching via tray icon or CLI flags.
