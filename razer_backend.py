"""Thin wrapper over the openrazer Python client (tested names: openrazer-daemon 3.12.x).

Replaces every sysfs read/write in open_chroma.py. Calls marked `# verify` use
client API names I have not run against your install.
"""
import logging
from typing import Optional

logger = logging.getLogger("OpenChroma.razer")

try:
    from openrazer.client import DeviceManager
    from openrazer.client.devices import RazerDevice
except ImportError:  # python3-openrazer not installed
    DeviceManager = None


class RazerBackend:
    """Finds the first keyboard and first mouse and exposes safe setters."""

    def __init__(self):
        self.error: Optional[str] = None
        self.devices = {"keyboard": None, "mouse": None}
        # The Naga Trinity accepts brightness values but does not dim its static
        # effect, so for these kinds the color itself is scaled in software.
        self.software_dim = {"mouse"}
        self._color = {"keyboard": (0, 255, 0), "mouse": (0, 255, 0)}
        self._level = {"keyboard": 100, "mouse": 100}
        self._connect()

    # ---- discovery ---------------------------------------------------------
    def _connect(self):
        if DeviceManager is None:
            self.error = "python3-openrazer is not installed"
            return
        try:
            manager = DeviceManager()
            manager.sync_effects = False  # keyboard and mouse get independent effects
            for dev in manager.devices:
                kind = "keyboard" if dev.type == "keyboard" else "mouse" if dev.type == "mouse" else None
                if kind and self.devices[kind] is None:
                    self.devices[kind] = dev
            self._manager = manager  # keep alive so D-Bus signals stay connected
        except Exception as e:  # DaemonNotFoundError and D-Bus errors
            self.error = f"openrazer-daemon not reachable: {e}"
        if self.error:
            logger.warning(self.error)

    def name(self, kind: str) -> str:
        dev = self.devices.get(kind)
        return dev.name if dev else f"No {kind} found"

    def is_mmo_mouse(self) -> bool:
        dev = self.devices["mouse"]
        return bool(dev and "naga" in dev.name.lower())

    def has(self, kind: str, capability: str) -> bool:
        """Capability names are the exact keys you printed, e.g. 'dpi', 'lighting_static'."""
        dev = self.devices.get(kind)
        try:
            return bool(dev and dev.has(capability))
        except Exception:
            return False

    # ---- lighting ----------------------------------------------------------
    def set_static(self, kind: str, r: int, g: int, b: int) -> bool:
        dev = self.devices.get(kind)
        if not dev or not self.has(kind, "lighting_static"):
            return False
        self._color[kind] = (r, g, b)
        if kind in self.software_dim:
            scale = self._level[kind] / 100.0
            r, g, b = (round(c * scale) for c in (r, g, b))
        try:
            dev.fx.static(r, g, b)
            # Naga zones (logo, scroll wheel) are separate capabilities.
            if self.has(kind, "lighting_logo_static"):
                dev.fx.misc.logo.static(r, g, b)  # verify
            if self.has(kind, "lighting_scroll_static"):
                dev.fx.misc.scroll_wheel.static(r, g, b)  # verify
            return True
        except Exception as e:
            logger.warning("set_static(%s) failed: %s", kind, e)
            return False

    def set_breathing(self, kind: str, r: int, g: int, b: int) -> bool:
        """Native single-color breathing. Has no min/max range or speed control."""
        dev = self.devices.get(kind)
        if not dev or not self.has(kind, "lighting_breath_single"):
            return False
        try:
            dev.fx.breath_single(r, g, b)  # verify
            return True
        except Exception as e:
            logger.warning("set_breathing(%s) failed: %s", kind, e)
            return False

    def set_brightness(self, kind: str, percent: int) -> bool:
        dev = self.devices.get(kind)
        if not dev or not self.has(kind, "brightness"):
            return False
        level = max(0, min(100, int(percent)))
        self._level[kind] = level
        try:
            if kind in self.software_dim:
                dev.brightness = 100  # keep the device at full so dimming is not applied twice
                return self.set_static(kind, *self._color[kind])
            dev.brightness = level
            return True
        except Exception as e:
            logger.warning("set_brightness(%s) failed: %s", kind, e)
            return False

    # ---- performance -------------------------------------------------------
    def set_dpi(self, dpi: int) -> bool:
        dev = self.devices["mouse"]
        if not dev or not self.has("mouse", "dpi"):
            return False
        try:
            dev.dpi = (dpi, dpi)
            return True
        except Exception as e:
            logger.warning("set_dpi(%s) failed: %s", dpi, e)
            return False

    def get_dpi(self) -> Optional[int]:
        dev = self.devices["mouse"]
        try:
            return dev.dpi[0] if dev and self.has("mouse", "dpi") else None
        except Exception:
            return None

    def supported_poll_rates(self) -> list:
        dev = self.devices["mouse"]
        try:
            if dev and self.has("mouse", "supported_poll_rates"):
                return sorted(dev.supported_poll_rates)
        except Exception:
            pass
        return [125, 500, 1000]

    def set_poll_rate(self, hz: int) -> bool:
        dev = self.devices["mouse"]
        if not dev or not self.has("mouse", "poll_rate"):
            return False
        try:
            dev.poll_rate = hz
            return True
        except Exception as e:
            logger.warning("set_poll_rate(%s) failed: %s", hz, e)
            return False

    def get_poll_rate(self) -> Optional[int]:
        dev = self.devices["mouse"]
        try:
            return int(dev.poll_rate) if dev and self.has("mouse", "poll_rate") else None
        except Exception:
            return None
