"""Thin wrapper over OpenRazer + automated OpenRGB client for 3-zone mouse lighting."""
import logging
import socket
import subprocess
import time
from typing import Optional

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
    HAS_OPENRGB = True
except ImportError:
    OpenRGBClient = None
    RGBColor = None
    HAS_OPENRGB = False

try:
    from openrazer.client import DeviceManager
except ImportError:
    DeviceManager = None

__version__ = "1.1.0"

logger = logging.getLogger("OpenChroma.razer")

OPENRGB_HOST = "127.0.0.1"
OPENRGB_PORT = 6742
OPENRGB_FLATPAK_APP = "org.openrgb.OpenRGB"
DEFAULT_SCROLL_RGB = (0, 255, 0)
DEFAULT_LOGO_RGB = (0, 255, 0)
DEFAULT_KEYPAD_RGB = (255, 255, 0)


def _port_open(host: str = OPENRGB_HOST, port: int = OPENRGB_PORT, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _connect_rgb_client(host: str = OPENRGB_HOST, port: int = OPENRGB_PORT, name: str = "OpenChroma") -> OpenRGBClient:
    """Connect to OpenRGB SDK server while guarding against EffectsPlugin StopIteration."""
    if OpenRGBClient is not None:
        OpenRGBClient.update_plugins = lambda self: None
    try:
        return OpenRGBClient(host, port, name)
    except StopIteration as exc:
        raise RuntimeError(
            "OpenRGBClient encountered StopIteration during plugin packet parsing"
        ) from exc


class RazerBackend:
    """Finds keyboard/mouse devices and automates lighting without manual daemon steps."""

    def __init__(self, auto_start_rgb: bool = True):
        self.version = __version__
        self.auto_start_rgb = auto_start_rgb
        self.error: Optional[str] = None
        self.devices = {"keyboard": None, "mouse": None}
        self.software_dim = {"mouse"}
        self._color = {"keyboard": (0, 255, 0), "mouse": (0, 255, 0)}
        self._mouse_zones: Optional[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = None
        self._level = {"keyboard": 100, "mouse": 100}
        self._rgb_client: Optional[OpenRGBClient] = None
        self._rgb_proc: Optional[subprocess.Popen] = None
        self._connect()

    def _connect(self):
        if DeviceManager is None:
            self.error = "python3-openrazer is not installed"
            return
        try:
            manager = DeviceManager()
            manager.sync_effects = False
            for dev in manager.devices:
                dev_type = getattr(dev, "type", "").lower()
                dev_name = getattr(dev, "name", "").lower()
                kind = None
                if "keyboard" in dev_type or any(
                    k in dev_name for k in ["ornata", "blackwidow", "huntsman", "deathstalker", "keyboard"]
                ):
                    kind = "keyboard"
                elif "mouse" in dev_type or any(
                    m in dev_name for m in ["naga", "deathadder", "basilisk", "viper", "mouse"]
                ):
                    kind = "mouse"
                if kind and self.devices[kind] is None:
                    self.devices[kind] = dev
                    logger.info("Discovered Razer %s: %s", kind, dev.name)
            self._manager = manager
        except Exception as e:
            self.error = f"openrazer-daemon not reachable: {e}"
        if self.error:
            logger.warning(self.error)

    def _ensure_rgb_client(self) -> Optional[OpenRGBClient]:
        if not HAS_OPENRGB or OpenRGBClient is None:
            logger.warning("openrgb Python client not installed")
            return None

        if not _port_open():
            if not self.auto_start_rgb:
                return None
            try:
                self._rgb_proc = subprocess.Popen(
                    [
                        "flatpak",
                        "run",
                        OPENRGB_FLATPAK_APP,
                        "--gui",
                        "--startminimized",
                        "--server",
                        "--server-port",
                        str(OPENRGB_PORT),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                for _ in range(50):
                    if _port_open():
                        break
                    time.sleep(0.1)
            except Exception as e:
                logger.warning("Failed to auto-start OpenRGB server: %s", e)
                return None

        if not _port_open():
            return None

        try:
            if self._rgb_client is None:
                self._rgb_client = _connect_rgb_client(
                    OPENRGB_HOST, OPENRGB_PORT, name="OpenChroma"
                )
            return self._rgb_client
        except Exception as e:
            logger.warning("Failed to connect OpenRGBClient: %s", e)
            self._rgb_client = None
            return None

    def stop_rgb_server(self) -> None:
        """Stops OpenRGB cleanly (e.g., after a game window stays open or on exit)."""
        self._rgb_client = None
        if self._rgb_proc and self._rgb_proc.poll() is None:
            self._rgb_proc.terminate()
            try:
                self._rgb_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._rgb_proc.kill()
        self._rgb_proc = None
        subprocess.run(["flatpak", "kill", OPENRGB_FLATPAK_APP], check=False)
        subprocess.run(["pkill", "-f", "openrgb.*--server"], check=False)

    def _scale_mouse_rgb(self, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        scale = self._level["mouse"] / 100.0
        return tuple(max(0, min(255, int(round(c * scale)))) for c in rgb)

    def _commit_rgb_device(self, device) -> None:
        for method_name in ("show", "update"):
            fn = getattr(device, method_name, None)
            if callable(fn):
                try:
                    fn()
                    return
                except Exception:
                    pass

    def _select_rgb_mouse_mode(self, mouse) -> None:
        modes = getattr(mouse, "modes", None) or []
        mode_names = [getattr(m, "name", "") for m in modes if getattr(m, "name", "")]
        for preferred in ("direct", "static"):
            for m_name in mode_names:
                if m_name.strip().lower() == preferred:
                    mouse.set_mode(m_name)
                    return
        if mode_names:
            try:
                mouse.set_mode(mode_names[0])
            except Exception as err:
                logger.debug("OpenRGB mouse fallback mode set ignored: %s", err)

    def name(self, kind: str) -> str:
        dev = self.devices.get(kind)
        return dev.name if dev else f"No {kind} found"

    def is_mmo_mouse(self) -> bool:
        dev = self.devices["mouse"]
        return bool(dev and "naga" in dev.name.lower())

    def has(self, kind: str, capability: str) -> bool:
        dev = self.devices.get(kind)
        try:
            return bool(dev and dev.has(capability))
        except Exception:
            return False

    def paint_mouse_zones(
        self,
        scroll_rgb=DEFAULT_SCROLL_RGB,
        logo_rgb=DEFAULT_LOGO_RGB,
        keypad_rgb=DEFAULT_KEYPAD_RGB,
    ) -> bool:
        """Paints the 3 mouse zones on launch, profile switch, or manual change."""
        return self.set_mouse_zones(scroll_rgb, logo_rgb, keypad_rgb)

    def set_mouse_zones(self, scroll_rgb, logo_rgb, keypad_rgb) -> bool:
        scroll_t = tuple(int(c) for c in scroll_rgb)
        logo_t = tuple(int(c) for c in logo_rgb)
        keypad_t = tuple(int(c) for c in keypad_rgb)
        self._mouse_zones = (scroll_t, logo_t, keypad_t)

        s_rgb = self._scale_mouse_rgb(scroll_t)
        l_rgb = self._scale_mouse_rgb(logo_t)
        k_rgb = self._scale_mouse_rgb(keypad_t)
        self._color["mouse"] = l_rgb

        client = self._ensure_rgb_client()
        if client is None or RGBColor is None:
            logger.warning("set_mouse_zones skipped: OpenRGB client unavailable")
            return False

        try:
            try:
                client.update()
            except Exception:
                pass

            mice = [
                d for d in client.devices
                if "naga trinity" in d.name.lower()
                or "naga" in d.name.lower()
                or "mouse" in d.name.lower()
            ]
            if not mice:
                logger.warning(
                    "OpenRGB connected, but no mouse matched in devices: %s",
                    [getattr(d, "name", "") for d in client.devices],
                )
                return False

            mouse = mice[0]
            try:
                self._select_rgb_mouse_mode(mouse)
            except Exception as mode_err:
                logger.warning("OpenRGB mouse mode selection failed: %s", mode_err)

            zone_colors = [s_rgb, l_rgb, k_rgb]
            named_map = {
                "scroll wheel": s_rgb,
                "logo": l_rgb,
                "numpad": k_rgb,
                "keypad": k_rgb,
            }

            if mouse.zones:
                matched_any = False
                for zone in mouse.zones:
                    z_rgb = named_map.get(zone.name.strip().lower())
                    if z_rgb is not None:
                        zone.set_color(RGBColor(*z_rgb))
                        matched_any = True
                if not matched_any:
                    for idx, zone in enumerate(mouse.zones[:3]):
                        zone.set_color(RGBColor(*zone_colors[idx]))
            else:
                colors = [RGBColor(*c) for c in zone_colors]
                led_count = len(mouse.leds)
                if led_count >= 3:
                    per_third = max(1, led_count // 3)
                    led_list = [colors[min(2, i // per_third)] for i in range(led_count)]
                    mouse.set_colors(led_list)
                elif led_count > 0:
                    mouse.set_color(colors[0])

            self._commit_rgb_device(mouse)
            return True
        except Exception as e:
            logger.warning("set_mouse_zones via OpenRGB failed: %s", e)
            self._rgb_client = None
            return False

    def set_static(self, kind: str, r: int, g: int, b: int) -> bool:
        dev = self.devices.get(kind)
        if not dev or not self.has(kind, "lighting_static"):
            return False
        self._color[kind] = (r, g, b)
        if kind == "mouse":
            self._mouse_zones = None
            r, g, b = self._scale_mouse_rgb((r, g, b))
        try:
            dev.fx.static(r, g, b)
            if self.has(kind, "lighting_logo_static"):
                dev.fx.misc.logo.static(r, g, b)
            if self.has(kind, "lighting_scroll_static"):
                dev.fx.misc.scroll_wheel.static(r, g, b)
            return True
        except Exception as e:
            logger.warning("set_static(%s) failed: %s", kind, e)
            return False

    def set_breathing(self, kind: str, r: int, g: int, b: int) -> bool:
        dev = self.devices.get(kind)
        if not dev or not self.has(kind, "lighting_breath_single"):
            return False
        if kind == "mouse":
            self._mouse_zones = None
        try:
            dev.fx.breath_single(r, g, b)
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
                if self._mouse_zones is not None:
                    return self.set_mouse_zones(*self._mouse_zones)
                return self.set_static(kind, *self._color[kind])
            dev.brightness = level
            return True
        except Exception as e:
            logger.warning("set_brightness(%s) failed: %s", kind, e)
            return False

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

    def apply_startup_lighting(
        self,
        scroll_rgb=DEFAULT_SCROLL_RGB,
        logo_rgb=DEFAULT_LOGO_RGB,
        keypad_rgb=DEFAULT_KEYPAD_RGB,
    ) -> bool:
        """Applies mouse zone lighting on application startup."""
        return self.paint_mouse_zones(scroll_rgb, logo_rgb, keypad_rgb)

    def apply_profile_lighting(
        self,
        scroll_rgb=DEFAULT_SCROLL_RGB,
        logo_rgb=DEFAULT_LOGO_RGB,
        keypad_rgb=DEFAULT_KEYPAD_RGB,
    ) -> bool:
        """Applies mouse zone lighting when switching profiles."""
        return self.paint_mouse_zones(scroll_rgb, logo_rgb, keypad_rgb)

    def apply_manual_lighting(
        self,
        scroll_rgb=DEFAULT_SCROLL_RGB,
        logo_rgb=DEFAULT_LOGO_RGB,
        keypad_rgb=DEFAULT_KEYPAD_RGB,
    ) -> bool:
        """Applies mouse zone lighting from a manual UI action."""
        return self.paint_mouse_zones(scroll_rgb, logo_rgb, keypad_rgb)