#!/usr/bin/env python3

# ==============================================================================
# OPENCHROMA - UNIVERSAL PERIPHERAL CONTROL UTILITY FOR LINUX (UNIVERSAL)
# Author: TLJTravis
# Description: Per-profile key remapping, automated window switching, and Chroma lighting.
# Supports Wayland & X11 across GNOME, Cinnamon, KDE, and XFCE via multi-backend detection.
# ==============================================================================

import sys, json, os, glob, subprocess, logging, threading, time, urllib.request
from pathlib import Path

# Ensure Python looks in the script's own folder for local modules (e.g. razer_backend)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from threading import Thread
from PyQt6.QtWidgets import (QApplication, QWidget, QGridLayout, QPushButton,
                             QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QButtonGroup, QMessageBox, QFileDialog, 
                             QTabWidget, QFrame, QSlider, QInputDialog,
                             QSystemTrayIcon, QMenu, QCheckBox, QStyle)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRectF
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QMouseEvent, QPen, QFont, QIcon, QAction, QPixmap

try:
    import dbus
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False

import evdev
from evdev import UInput, ecodes as e
from razer_backend import RazerBackend

# ==============================================================================
# GLOBAL CONFIGURATION & CONSTANTS
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("OpenChroma-Universal")

PROFILE_FILE = os.path.expanduser("~/.config/naga_profiles.json")
RAZER_VENDOR_ID = 0x1532

# ==============================================================================
# HARDWARE IMAGE CACHING HELPER
# ==============================================================================
def get_cached_device_image(device_name, image_url, fallback="OpenChroma"):
    cache_dir = os.path.expanduser("~/.cache/openchroma/images")
    os.makedirs(cache_dir, exist_ok=True)
    
    if not device_name:
        device_name = "unknown_device"
        
    safe_name = str(device_name).lower().replace(" ", "_") + ".png"
    local_path = os.path.join(cache_dir, safe_name)
    
    if os.path.exists(local_path) and os.path.getsize(local_path) < 100:
        os.remove(local_path)
    
    if not os.path.exists(local_path) and image_url:
        try:
            urllib.request.urlretrieve(image_url, local_path)
            if os.path.exists(local_path) and os.path.getsize(local_path) < 100:
                os.remove(local_path)
        except Exception as e:
            logger.debug(f"Failed to download device image: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            
    if not os.path.exists(local_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_path = os.path.join(script_dir, "assets", f"{fallback}.png")
        if os.path.exists(fallback_path):
            return fallback_path
            
    return local_path if os.path.exists(local_path) else None

# ==============================================================================
# 0. DPI OSD NOTIFICATION POPUP WIDGET
# ==============================================================================
class DpiOsdOverlay(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(24, 24, 24, 235);
                color: #00ff00;
                border: 2px solid #00ff00;
                border-radius: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer = QTimer()
        self.timer.timeout.connect(self.hide)

    def show_dpi(self, dpi_val):
        self.setText(f"DPI: {dpi_val}")
        self.adjustSize()
        
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 200
        y = screen.bottom() - self.height() - 200
        self.move(x, y)
        
        self.show()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.timer.start(1200)

# ==============================================================================
# 1. EMBEDDED 16M GAMUT COLOR SPECTRUM WIDGET
# ==============================================================================
class GamutSpectrumWidget(QWidget):
    colorSelected = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.selected_point = QPoint(50, 60)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        gradient.setColorAt(0.00, QColor(255, 0, 0))
        gradient.setColorAt(0.17, QColor(255, 255, 0))
        gradient.setColorAt(0.33, QColor(0, 255, 0))
        gradient.setColorAt(0.50, QColor(0, 255, 255))
        gradient.setColorAt(0.67, QColor(0, 0, 255))
        gradient.setColorAt(0.83, QColor(255, 0, 255))
        gradient.setColorAt(1.00, QColor(255, 0, 0))

        painter.fillRect(rect, gradient)

        shade_grad = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        shade_grad.setColorAt(0.0, QColor(255, 255, 255, 200))
        shade_grad.setColorAt(0.5, QColor(0, 0, 0, 0))
        shade_grad.setColorAt(1.0, QColor(0, 0, 0, 230))
        painter.fillRect(rect, shade_grad)

        painter.setPen(Qt.GlobalColor.white)
        painter.drawEllipse(self.selected_point, 5, 5)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawEllipse(self.selected_point, 6, 6)

    def mousePressEvent(self, event: QMouseEvent):
        self.pick_color(event.position().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.pick_color(event.position().toPoint())

    def pick_color(self, pt):
        x = max(0, min(pt.x(), self.width() - 1))
        y = max(0, min(pt.y(), self.height() - 1))
        self.selected_point = QPoint(x, y)
        
        img = self.grab().toImage()
        col = img.pixelColor(x, y)
        self.colorSelected.emit(col)
        self.update()

# ==============================================================================
# 2. UNIVERSAL AUTO-PROFILE WORKER THREAD (GNOME DBUS + X11 FALLBACK)
# ==============================================================================
class SignalBridge(QWidget):
    window_changed_signal = pyqtSignal(tuple)

class AutoProfileWorker(Thread):
    def __init__(self, signals_emitter, shutdown_event):
        super().__init__()
        self.emitter = signals_emitter
        self.shutdown_event = shutdown_event
        self.daemon = True
        self.last_seen_window = None
        self.session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()

    def get_active_window_info(self):
        wm_class = ""
        title = ""
        
        # 1. X11 Backend (Linux Mint / Xorg / Cinnamon) using xdotool
        if self.session_type != "wayland" or os.environ.get("DISPLAY"):
            try:
                class_res = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowclassname"], 
                    capture_output=True, text=True, timeout=0.2
                )
                if class_res.returncode == 0:
                    wm_class = class_res.stdout.strip().lower()
                    
                title_res = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"], 
                    capture_output=True, text=True, timeout=0.2
                )
                if title_res.returncode == 0:
                    title = title_res.stdout.strip().lower()
                    
                if wm_class or title:
                    return "x11_win", [wm_class], title
            except Exception:
                pass

        # 2. Wayland / GNOME Shell DBus Backend
        if HAS_DBUS:
            try:
                session_bus = dbus.SessionBus()
                gnome_obj = session_bus.get_object('org.gnome.Shell', '/org/gnome/Shell')
                gnome_iface = dbus.Interface(gnome_obj, 'org.gnome.Shell')
                
                js_code = 'global.display.focus_window ? global.display.focus_window.get_wm_class() + ":::" + global.display.focus_window.get_title() : ""'
                result = gnome_iface.Eval(js_code)
                
                if result and result[0] and result[1]:
                    val = str(result[1]).strip()
                    if ":::" in val:
                        w_class, w_title = val.split(":::", 1)
                        return "wayland_win", [w_class.lower().strip()], w_title.lower().strip()
            except Exception:
                pass

        return "", [], ""

    def run(self):
        while not self.shutdown_event.is_set():
            win_id, class_tokens, window_title = self.get_active_window_info()
            combined_key = (win_id, tuple(class_tokens), window_title)
            if combined_key != self.last_seen_window:
                self.last_seen_window = combined_key
                self.emitter.window_changed_signal.emit((win_id, class_tokens, window_title))
            
            if self.shutdown_event.wait(1.5):
                break

# ==============================================================================
# 3. LIVE INPUT DAEMON (MULTI-DEVICE SCANNER & UINPUT)
# ==============================================================================
class LiveInputDaemon(Thread):
    def __init__(self, get_current_profile_bindings_callback, app_reference, shutdown_event):
        super().__init__()
        self.daemon = True
        self.get_bindings = get_current_profile_bindings_callback
        self.app = app_reference
        self.shutdown_event = shutdown_event
        self.uinput = None

    def init_uinput(self):
        try:
            capabilities = {
                e.EV_KEY: [
                    e.KEY_A, e.KEY_B, e.KEY_C, e.KEY_D, e.KEY_E, e.KEY_F, e.KEY_G,
                    e.KEY_H, e.KEY_I, e.KEY_J, e.KEY_K, e.KEY_L, e.KEY_M, e.KEY_N,
                    e.KEY_O, e.KEY_P, e.KEY_Q, e.KEY_R, e.KEY_S, e.KEY_T, e.KEY_U,
                    e.KEY_V, e.KEY_W, e.KEY_X, e.KEY_Y, e.KEY_Z,
                    e.KEY_1, e.KEY_2, e.KEY_3, e.KEY_4, e.KEY_5, e.KEY_6, e.KEY_7,
                    e.KEY_8, e.KEY_9, e.KEY_0, e.KEY_MINUS, e.KEY_EQUAL,
                    e.KEY_LEFTCTRL, e.KEY_LEFTSHIFT, e.KEY_LEFTALT,
                    e.KEY_F1, e.KEY_F2, e.KEY_F3, e.KEY_F4, e.KEY_F5, e.KEY_F6,
                    e.KEY_F7, e.KEY_F8, e.KEY_F9, e.KEY_F10, e.KEY_F11, e.KEY_F12,
                    e.BTN_LEFT, e.BTN_RIGHT, e.BTN_MIDDLE, e.BTN_SIDE, e.BTN_EXTRA
                ],
                e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL]
            }
            self.uinput = UInput(capabilities, name="OpenChroma-Virtual-Input")
            logger.info("Initialized evdev UInput virtual device.")
        except Exception as err:
            logger.error(f"Failed to create UInput device: {err}")

    def find_mouse_keypad_device(self):
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                if dev.info.vendor != RAZER_VENDOR_ID:
                    continue
                caps = dev.capabilities()
                if evdev.ecodes.EV_KEY in caps and evdev.ecodes.EV_REL not in caps:
                    keys = caps[evdev.ecodes.EV_KEY]
                    if all(k in keys for k in range(2, 10)) or any(b in keys for b in [e.BTN_SIDE, e.BTN_EXTRA]):
                        logger.info(f"Discovered Razer mouse keypad: {dev.name} at {path}")
                        return dev
            except Exception as err:
                logger.debug(f"Error inspecting device {path}: {err}")
        return None

    def send_combo_uinput(self, action_str, is_press):
        if not self.uinput:
            return

        if "Click" in action_str:
            click_map = {
                "Left Click": e.BTN_LEFT, "Right Click": e.BTN_RIGHT,
                "Middle Click": e.BTN_MIDDLE
            }
            if action_str in click_map and is_press:
                self.uinput.write(e.EV_KEY, click_map[action_str], 1)
                self.uinput.syn()
            elif action_str in click_map and not is_press:
                self.uinput.write(e.EV_KEY, click_map[action_str], 0)
                self.uinput.syn()
            return

        key_map = {
            "ctrl": e.KEY_LEFTCTRL, "control": e.KEY_LEFTCTRL,
            "shift": e.KEY_LEFTSHIFT, "alt": e.KEY_LEFTALT,
            "1": e.KEY_1, "2": e.KEY_2, "3": e.KEY_3, "4": e.KEY_4, "5": e.KEY_5,
            "6": e.KEY_6, "7": e.KEY_7, "8": e.KEY_8, "9": e.KEY_9, "0": e.KEY_0,
            "-": e.KEY_MINUS, "=": e.KEY_EQUAL,
            "a": e.KEY_A, "b": e.KEY_B, "c": e.KEY_C, "d": e.KEY_D, "e": e.KEY_E,
            "f": e.KEY_F, "g": e.KEY_G, "h": e.KEY_H, "i": e.KEY_I, "j": e.KEY_J,
            "k": e.KEY_K, "l": e.KEY_L, "m": e.KEY_M, "n": e.KEY_N, "o": e.KEY_O,
            "p": e.KEY_P, "q": e.KEY_Q, "r": e.KEY_R, "s": e.KEY_S, "t": e.KEY_T,
            "u": e.KEY_U, "v": e.KEY_V, "w": e.KEY_W, "x": e.KEY_X, "y": e.KEY_Y,
            "z": e.KEY_Z
        }

        parts = [p.lower().strip() for p in action_str.split("+")]
        codes = [key_map[p] for p in parts if p in key_map]

        if is_press:
            for code in codes:
                self.uinput.write(e.EV_KEY, code, 1)
        else:
            for code in reversed(codes):
                self.uinput.write(e.EV_KEY, code, 0)
        self.uinput.syn()

    def run(self):
        from select import select
        self.init_uinput()
        
        mouse_dev = self.find_mouse_keypad_device()
        if not mouse_dev:
            logger.error("LiveInputDaemon aborted: No Razer mouse keypad found.")
            return
        
        try:
            mouse_dev.grab()
            logger.info(f"Successfully grabbed mouse keypad: {mouse_dev.name}")
        except Exception as err:
            logger.error(f"Permission denied grabbing keypad: {err}")
            return

        hardware_button_map = {
            2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6",
            8: "7", 9: "8", 10: "9", 11: "10", 12: "11", 13: "12"
        }
        trinity_map = {
            2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6",
            8: "7", 9: "8", 10: "9", 11: "10", 12: "11", 13: "12",
            e.BTN_MIDDLE: "Top_M", e.BTN_FORWARD: "Top_Forward", e.BTN_BACK: "Top_Back"
        }

        try:
            while not self.shutdown_event.is_set():
                r, w, x = select([mouse_dev.fileno()], [], [], 0.1)
                if mouse_dev.fileno() in r:
                    for event in mouse_dev.read():
                        bindings = self.get_bindings()
                        if event.type != evdev.ecodes.EV_KEY:
                            continue
                        
                        button_str = hardware_button_map.get(event.code, trinity_map.get(event.code))
                        if button_str and button_str in bindings:
                            target_action = bindings[button_str]
                            if target_action:
                                self.send_combo_uinput(target_action, event.value == 1)
        except Exception as err:
            logger.error(f"Exception in input loop: {err}")
        finally:
            try:
                mouse_dev.ungrab()
            except Exception:
                pass
            if self.uinput:
                self.uinput.close()

# ==============================================================================
# 4. MAIN GUI APPLICATION & SYNAPSE CONTROL PANEL
# ==============================================================================
class NagaSynapseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setProperty("class", "openchroma")
        self.setWindowRole("openchroma")
        
        self.active_button_name, self.is_recording = None, False
        self.current_combo = set()
        self.current_active_panel = None
        self.hw_buttons = {}
        self.thumb_buttons = {}
        self.saved_geometry = None
        
        self.shutdown_event = threading.Event()
        self.profiles = self.load_profiles()
        self.razer = RazerBackend()
        self.is_mmo_mouse = self.detect_mmo_mouse()
        
        self.current_target = "mouse"
        self.device_states = {
            "mouse": {
                "color": QColor(0, 255, 0),
                "effect": "Static (Custom Color)",
                "brightness": 100,
                "breathe_min": 10,
                "breathe_max": 100,
                "breathe_speed": 2,
                "breathe_val": 50,
                "breathe_dir": 1
            },
            "keyboard": {
                "color": QColor(0, 255, 0),
                "effect": "Static (Custom Color)",
                "brightness": 100,
                "breathe_min": 10,
                "breathe_max": 100,
                "breathe_speed": 2,
                "breathe_val": 50,
                "breathe_dir": 1
            }
        }

        self.dpi_stages = [300, 800, 1800, 3200, 4800, 6400, 7600, 9200, 12000]
        self.current_dpi_index = 2
        self.osd = DpiOsdOverlay()

        self.master_breathe_timer = QTimer(self)
        self.master_breathe_timer.timeout.connect(self.run_independent_breathe_steps)
        self.master_breathe_timer.start(40)

        self.profile_dropdowns = []
        self.initUI()
        self.update_detected_hardware_labels()
        self.change_profile(0)

        self.bridge = SignalBridge()
        self.bridge.window_changed_signal.connect(self.handle_auto_window_switch)
        
        self.switcher = AutoProfileWorker(self.bridge, self.shutdown_event)
        self.switcher.start()

        self.input_daemon = LiveInputDaemon(self.get_active_bindings, self, self.shutdown_event)
        self.input_daemon.start()

        if self.is_mmo_mouse:
            self.set_panel_view("12-button")
        else:
            self.set_panel_view("2-button")

    def showEvent(self, event):
        super().showEvent(event)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "assets", "OpenChroma.png")
        if os.path.exists(icon_path) and self.windowHandle():
            self.windowHandle().setIcon(QIcon(icon_path))

    def changeEvent(self, event):
        if self.isMinimized() or not self.isVisible():
            self.saved_geometry = self.geometry()
        super().changeEvent(event)

    def closeEvent(self, event):
        logger.info("Initiating clean shutdown for OpenChroma...")
        self.shutdown_event.set()
        self.switcher.join(timeout=1.0)
        self.input_daemon.join(timeout=1.0)
        event.accept()

    def detect_mmo_mouse(self):
        if self.razer.is_mmo_mouse():
            logger.info(f"Detected MMO mouse: {self.razer.name('mouse')}")
            return True
        logger.warning("No Naga detected via openrazer; defaulting to standard layout.")
        return False

    def _apply_hw_dpi(self, dpi):
        if getattr(self, "_last_hw_dpi", None) != dpi and self.razer.set_dpi(dpi):
            self._last_hw_dpi = dpi

    def set_exact_dpi_preset(self, target_dpi, trigger_osd=False):
        self.dpi_slider.blockSignals(True)
        self.dpi_slider.setValue(target_dpi)
        self.dpi_slider.blockSignals(False)
        self.dpi_label.setText(f"Current DPI: <b>{target_dpi}</b> (Preset Stage)")
        if target_dpi in self.dpi_stages:
            self.current_dpi_index = self.dpi_stages.index(target_dpi)

        curr_prof = self.get_active_profile_name()
        if curr_prof in self.profiles and isinstance(self.profiles[curr_prof], dict):
            if "bindings" in self.profiles[curr_prof]:
                self.profiles[curr_prof]["dpi"] = target_dpi
            else:
                bindings = self.profiles[curr_prof].copy()
                self.profiles[curr_prof] = {"bindings": bindings, "dpi": target_dpi}

        self._apply_hw_dpi(target_dpi)
        if trigger_osd:
            self.osd.show_dpi(target_dpi)

    def on_dpi_slider_changed(self, value):
        closest_dpi = min(self.dpi_stages, key=lambda x: abs(x - value))
        self.set_exact_dpi_preset(closest_dpi, trigger_osd=False)

    def initUI(self):
        self.setWindowTitle('OpenChroma Controls (Universal - 1.0.6)')
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "assets", "OpenChroma.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QWidget { 
                background-color: #181818; 
                color: #e0e0e0; 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 13px;
            }
            QTabWidget::pane { border: none; background-color: #181818; }
            QTabBar::tab { background-color: #121212; color: #888888; padding: 12px 24px; font-weight: bold; border-top: 3px solid transparent; }
            QTabBar::tab:selected { background-color: #181818; color: #00ff00; border-top: 3px solid #00ff00; }
            QTabBar::tab:hover { color: #ffffff; }
            QComboBox, QLineEdit { background-color: #222222; border: 1px solid #333333; padding: 6px 10px; color: #ffffff; border-radius: 3px; }
            QComboBox:hover, QLineEdit:hover { border: 1px solid #00ff00; }
            QPushButton { background-color: #222222; border: 1px solid #3a3a3a; border-radius: 4px; padding: 7px 14px; font-weight: bold; color: #ffffff; }
            QPushButton:hover { border: 1px solid #00ff00; background-color: #2a2a2a; }
            QPushButton:pressed { background-color: #00ff00; color: #000000; }
            QFrame#CardFrame { background-color: #1e1e1e; border: 1px solid #2c2c2c; border-radius: 6px; }
            QSlider::groove:horizontal { height: 6px; background: #222222; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00ff00; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffffff; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Device info card
        self.device_info_card = QFrame()
        self.device_info_card.setObjectName("CardFrame")
        info_layout = QHBoxLayout(self.device_info_card)
        info_layout.setContentsMargins(15, 10, 15, 10)
        
        self.keyboard_icon_lbl = QLabel()
        self.keyboard_icon_lbl.setFixedSize(50, 30)
        self.keyboard_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.keyboard_icon_lbl)
        
        self.keyboard_lbl = QLabel("<b>Keyboard:</b> Scanning...")
        self.keyboard_lbl.setStyleSheet("color: #00ff00; font-size: 12px;")
        info_layout.addWidget(self.keyboard_lbl)
        
        separator = QLabel("  |  ")
        separator.setStyleSheet("color: #888888; font-size: 12px;")
        info_layout.addWidget(separator)
        
        self.mouse_icon_lbl = QLabel()
        self.mouse_icon_lbl.setFixedSize(50, 30)
        self.mouse_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self.mouse_icon_lbl)
        
        self.mouse_lbl = QLabel("<b>Mouse:</b> Scanning...")
        self.mouse_lbl.setStyleSheet("color: #00ff00; font-size: 12px;")
        info_layout.addWidget(self.mouse_lbl)
        
        info_layout.addStretch()
        main_layout.addWidget(self.device_info_card)

        self.tabs = QTabWidget()
        
        # Customize Tab
        customize_tab = QWidget()
        customize_layout = QHBoxLayout(customize_tab)
        customize_layout.setContentsMargins(20, 20, 20, 20)
        customize_layout.setSpacing(20)

        left_card = QFrame()
        left_card.setObjectName("CardFrame")
        left_card_layout = QVBoxLayout(left_card)
        
        profile_bar = QHBoxLayout()
        prof_select_cust = QComboBox()
        prof_select_cust.addItems(self.get_profile_names())
        prof_select_cust.currentIndexChanged.connect(self.handle_dropdown_profile_change)
        self.profile_dropdowns.append(prof_select_cust)
        
        profile_bar.addWidget(QLabel("<b>PROFILE</b>"))
        profile_bar.addWidget(prof_select_cust)
        left_card_layout.addLayout(profile_bar)
        left_card_layout.addSpacing(10)

        mgmt_bar = QHBoxLayout()
        new_prof_btn = QPushButton("+ New")
        new_prof_btn.clicked.connect(self.create_profile)
        mgmt_bar.addWidget(new_prof_btn)
        
        delete_prof_btn = QPushButton("Delete")
        delete_prof_btn.setStyleSheet("background-color: #311111; color: #ff6666; border: 1px solid #5a1a1a;")
        delete_prof_btn.clicked.connect(self.delete_profile)
        mgmt_bar.addWidget(delete_prof_btn)

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_profiles)
        mgmt_bar.addWidget(export_btn)

        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_profiles)
        mgmt_bar.addWidget(import_btn)
        left_card_layout.addLayout(mgmt_bar)
        left_card_layout.addSpacing(15)

        left_card_layout.addWidget(QLabel("<b>ACTIVE PLATE LAYOUT & TOP BUTTONS</b>"))
        self.grid_container = QWidget()
        self.container_layout = QVBoxLayout(self.grid_container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        left_card_layout.addWidget(self.grid_container, alignment=Qt.AlignmentFlag.AlignCenter)

        thumb_bar = QHBoxLayout()
        thumb_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_bar.setSpacing(10)
        
        if self.is_mmo_mouse:
            thumbs_info = [
                ("top", "Top View"),
                ("2-button", "2-Btn"),
                ("7-button", "7-Btn"),
                ("12-button", "12-Btn")
            ]
        else:
            thumbs_info = [
                ("top", "Top View"),
                ("2-button", "Standard")
            ]
        
        for p_key, p_label in thumbs_info:
            btn = QPushButton(p_label)
            btn.setCheckable(True)
            btn.setFixedSize(85, 45)
            btn.clicked.connect(lambda checked, k=p_key: self.set_panel_view(k))
            thumb_bar.addWidget(btn)
            self.thumb_buttons[p_key] = btn
            
        left_card_layout.addLayout(thumb_bar)
        left_card_layout.addStretch()

        customize_layout.addWidget(left_card, stretch=2)

        # Right Panel - Keybindings & Mouse Functions
        right_card = QFrame()
        right_card.setObjectName("CardFrame")
        right_card_layout = QVBoxLayout(right_card)
        
        right_card_layout.addWidget(QLabel("<b style='color: #00ff00;'>KEYBOARD FUNCTION</b>"))
        self.target_label = QLabel("<i>Select a mouse button to configure</i>")
        self.target_label.setStyleSheet("color: #888888; font-size: 11px;")
        right_card_layout.addWidget(self.target_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Record a macro or type keybind...")
        right_card_layout.addWidget(self.key_input)
        
        self.record_btn = QPushButton("Record Keyboard Function")
        self.record_btn.clicked.connect(self.toggle_key_recording)
        right_card_layout.addWidget(self.record_btn)

        right_card_layout.addSpacing(10)
        right_card_layout.addWidget(QLabel("<b style='color: #00ff00;'>ASSIGN MOUSE FUNCTION</b>"))
        self.mouse_func_combo = QComboBox()
        self.mouse_func_combo.addItem("-- Select Mouse Function --")
        self.mouse_func_combo.addItems([
            "Left Click", "Right Click", "Middle Click", 
            "Back", "Forward", "Scroll Up", "Scroll Down",
            "Scroll Left", "Scroll Right"
        ])
        self.mouse_func_combo.currentIndexChanged.connect(self.handle_mouse_function_selection)
        right_card_layout.addWidget(self.mouse_func_combo)
        
        right_card_layout.addSpacing(20)
        apply_btn = QPushButton("SAVE & APPLY")
        apply_btn.setStyleSheet("background-color: #00ff00; color: #000000; font-weight: bold; border: none;")
        apply_btn.clicked.connect(self.save_to_disk)
        right_card_layout.addWidget(apply_btn)
        
        right_card_layout.addStretch()
        customize_layout.addWidget(right_card, stretch=1)

        self.tabs.addTab(customize_tab, "CUSTOMIZE")

        # Performance Tab
        perf_tab = self.build_performance_tab()
        self.tabs.addTab(perf_tab, "PERFORMANCE")

        # Lighting Tab
        light_tab = self.build_lighting_tab()
        self.tabs.addTab(light_tab, "LIGHTING")

        main_layout.addWidget(self.tabs)

        # --- Footer Layout (Autostart Checkbox) ---
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 0, 15, 8)
        footer_layout.addStretch()
        
        self.autostart_chk = QCheckBox("Open program on startup")
        self.autostart_chk.setChecked(self.check_autostart_status())
        self.autostart_chk.setStyleSheet("""
            QCheckBox {
                color: #00FF66;
                spacing: 5px;
            }
            QCheckBox::indicator {
                border: 1px solid #00FF66;
                background: #1e1e1e;
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background: #00FF66;
            }
        """)
        self.autostart_chk.toggled.connect(self.toggle_autostart)
        footer_layout.addWidget(self.autostart_chk)
        
        main_layout.addLayout(footer_layout)
        self.setLayout(main_layout)
        self.setFixedSize(980, 600)

        # --- System Tray Initialization ---
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            custom_icon = QIcon(pixmap)
            self.tray_icon.setIcon(custom_icon)
            self.setWindowIcon(custom_icon)
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        self.tray_menu = QMenu()
        
        self.show_action = QAction("Show OpenChroma", self)
        self.show_action.triggered.connect(self.showNormal)
        self.tray_menu.addAction(self.show_action)
        
        self.tray_menu.addSeparator()
        self.tray_profile_menu = self.tray_menu.addMenu("Switch Game Profile")
        self.update_tray_profile_menu()
        
        self.tray_menu.addSeparator()
        self.quit_action = QAction("Quit Program", self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.handle_tray_activation)
        self.tray_icon.show()

    def update_tray_profile_menu(self):
        if not hasattr(self, 'tray_profile_menu'):
            return
        self.tray_profile_menu.clear()
        for prof_name in self.get_profile_names():
            action = QAction(prof_name, self)
            action.triggered.connect(lambda checked, p=prof_name: self.select_profile_from_tray(p))
            self.tray_profile_menu.addAction(action)

    def select_profile_from_tray(self, profile_name):
        self.sync_all_profile_dropdowns(profile_name)
        self.change_profile(0)
        logger.info(f"Switched profile to '{profile_name}' via system tray.")

    def handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.saved_geometry = self.geometry()
                self.hide()
            else:
                self.showNormal()
                if self.saved_geometry is not None:
                    self.setGeometry(self.saved_geometry)
                self.activateWindow()

    def get_autostart_path(self) -> Path:
        return Path.home() / ".config" / "autostart" / "openchroma.desktop"

    def check_autostart_status(self) -> bool:
        return self.get_autostart_path().exists()

    def toggle_autostart(self, checked: bool):
        desktop_file = self.get_autostart_path()
        autostart_dir = desktop_file.parent

        if checked:
            try:
                autostart_dir.mkdir(parents=True, exist_ok=True)
                python_executable = sys.executable
                app_script = os.path.abspath(sys.argv[0])
                
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=OpenChroma
Comment=Razer RGB Device & Profile Manager
Exec={python_executable} {app_script}
Terminal=false
X-GNOME-Autostart-enabled=true
"""
                desktop_file.write_text(desktop_content.strip())
                logger.info(f"Created autostart entry at {desktop_file}")
            except Exception as e:
                logger.error(f"Failed to create autostart desktop entry: {e}")
                QMessageBox.critical(self, "Error", f"Could not create autostart entry: {e}")
        else:
            if desktop_file.exists():
                try:
                    desktop_file.unlink()
                    logger.info("Removed autostart entry.")
                except Exception as e:
                    logger.error(f"Failed to remove autostart desktop entry: {e}")
                    QMessageBox.critical(self, "Error", f"Could not remove autostart entry: {e}")

    def build_performance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)

        p_bar = QHBoxLayout()
        prof_select_perf = QComboBox()
        prof_select_perf.setFixedWidth(180)
        prof_select_perf.addItems(self.get_profile_names())
        prof_select_perf.currentIndexChanged.connect(self.handle_dropdown_profile_change)
        self.profile_dropdowns.append(prof_select_perf)
        
        p_bar.addWidget(QLabel("<b>PROFILE</b>"))
        p_bar.addWidget(prof_select_perf)
        p_bar.addStretch()
        
        save_perf_btn = QPushButton("SAVE & APPLY")
        save_perf_btn.setStyleSheet("background-color: #00ff00; color: #000000; font-weight: bold; border: none; padding: 6px 16px; border-radius: 4px;")
        save_perf_btn.clicked.connect(self.save_to_disk)
        p_bar.addWidget(save_perf_btn)
        
        card_layout.addLayout(p_bar)
        card_layout.addSpacing(15)

        dpi_header_banner = QLabel("  SENSITIVITY (DPI)")
        dpi_header_banner.setStyleSheet("background-color: #141414; color: #00ff00; font-weight: bold; font-size: 13px; padding: 6px 4px; border-radius: 3px;")
        card_layout.addWidget(dpi_header_banner)
        card_layout.addSpacing(10)
        
        self.dpi_label = QLabel("Current DPI: <b>1800</b> (Profile Preset)")
        self.dpi_label.setStyleSheet("font-size: 13px; margin-left: 5px;")
        card_layout.addWidget(self.dpi_label)
        card_layout.addSpacing(5)

        self.dpi_slider = QSlider(Qt.Orientation.Horizontal)
        self.dpi_slider.setMinimum(300)
        self.dpi_slider.setMaximum(12000)
        self.dpi_slider.setValue(1800)
        self.dpi_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #222222; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00ff00; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffffff; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
        """)
        self.dpi_slider.sliderMoved.connect(self.snap_dpi_slider)
        self.dpi_slider.sliderReleased.connect(self.finalize_snap_dpi)
        self.dpi_slider.valueChanged.connect(self.on_dpi_slider_changed)
        card_layout.addWidget(self.dpi_slider)

        card_layout.addSpacing(10)
        card_layout.addWidget(QLabel("<b>DPI Presets:</b>"))
        card_layout.addSpacing(5)
        
        stage_layout = QHBoxLayout()
        stage_layout.setSpacing(12)
        for stage_dpi in self.dpi_stages:
            btn = QPushButton(f"{stage_dpi}")
            btn.setFixedHeight(35)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #222222;
                    border: 1px solid #333333;
                    border-radius: 4px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border: 1px solid #00ff00;
                    background-color: #2a2a2a;
                }
            """)
            btn.clicked.connect(lambda checked, d=stage_dpi: self.set_exact_dpi_preset(d, trigger_osd=True))
            stage_layout.addWidget(btn)
        card_layout.addLayout(stage_layout)

        card_layout.addSpacing(15)
        
        outer_info_box = QFrame()
        outer_info_box.setStyleSheet("background-color: #121f12; border: 1px solid #00ff00; border-radius: 6px;")
        outer_layout = QVBoxLayout(outer_info_box)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        inner_info_box = QFrame()
        inner_info_box.setStyleSheet("border: 1px solid #00ff00; border-radius: 4px; background-color: transparent;")
        inner_layout = QVBoxLayout(inner_info_box)
        inner_layout.setContentsMargins(15, 12, 15, 12)

        info_text = QLabel("<b>Per-Profile DPI:</b> DPI stages now automatically save and load based on your active game profile.")
        info_text.setStyleSheet("border: none; color: #ffffff; font-size: 12px;")
        inner_layout.addWidget(info_text)

        outer_layout.addWidget(inner_info_box)
        card_layout.addWidget(outer_info_box)

        card_layout.addSpacing(15)

        poll_header_banner = QLabel("  POLLING RATE")
        poll_header_banner.setStyleSheet("background-color: #141414; color: #00ff00; font-weight: bold; font-size: 13px; padding: 6px 4px; border-radius: 3px;")
        card_layout.addWidget(poll_header_banner)
        card_layout.addSpacing(10)

        polling_layout = QHBoxLayout()
        self.poll_combo = QComboBox()
        self.poll_combo.setFixedWidth(120)
        rates = [f"{r} Hz" for r in self.razer.supported_poll_rates()]
        self.poll_combo.addItems(rates)
        current_rate = self.razer.get_poll_rate()
        if current_rate and f"{current_rate} Hz" in rates:
            self.poll_combo.setCurrentText(f"{current_rate} Hz")
        self.poll_combo.setEnabled(self.razer.has("mouse", "poll_rate"))
        self.poll_combo.currentTextChanged.connect(
            lambda text: self.razer.set_poll_rate(int(text.split()[0])))
        polling_layout.addWidget(self.poll_combo)
        polling_layout.addStretch()
        card_layout.addLayout(polling_layout)

        card_layout.addStretch()
        layout.addWidget(card)
        return tab

    def snap_dpi_slider(self, val):
        closest_dpi = min(self.dpi_stages, key=lambda x: abs(x - val))
        self.dpi_slider.blockSignals(True)
        self.dpi_slider.setValue(closest_dpi)
        self.dpi_slider.blockSignals(False)
        self.dpi_label.setText(f"Current DPI: <b>{closest_dpi}</b> (Profile Preset)")

    def finalize_snap_dpi(self):
        current_val = self.dpi_slider.value()
        closest_dpi = min(self.dpi_stages, key=lambda x: abs(x - current_val))
        self.set_exact_dpi_preset(closest_dpi, trigger_osd=False)

    def build_lighting_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)

        p_bar = QHBoxLayout()
        prof_select_light = QComboBox()
        prof_select_light.addItems(self.get_profile_names())
        prof_select_light.currentIndexChanged.connect(self.handle_dropdown_profile_change)
        self.profile_dropdowns.append(prof_select_light)
        
        p_bar.addWidget(QLabel("<b>PROFILE</b>"))
        p_bar.addWidget(prof_select_light)
        p_bar.addStretch()
        
        save_light_btn = QPushButton("SAVE & APPLY")
        save_light_btn.setStyleSheet("background-color: #00ff00; color: #000000; font-weight: bold; border: none; padding: 5px 12px;")
        save_light_btn.clicked.connect(self.save_to_disk)
        p_bar.addWidget(save_light_btn)
        
        card_layout.addLayout(p_bar)
        card_layout.addSpacing(10)

        card_layout.addWidget(QLabel("<b style='color: #00ff00; font-size: 15px;'>CHROMA LIGHTING EFFECTS (INDEPENDENT)</b>"))
        
        card_layout.addSpacing(5)
        card_layout.addWidget(QLabel("<b>SELECT COLOR TARGET</b>"))
        
        target_layout = QHBoxLayout()
        self.target_mouse_btn = QPushButton("Mouse")
        self.target_mouse_btn.setCheckable(True)
        self.target_mouse_btn.setChecked(True)
        self.target_mouse_btn.clicked.connect(lambda: self.set_color_target("mouse"))
        
        self.target_keyboard_btn = QPushButton("Keyboard")
        self.target_keyboard_btn.setCheckable(True)
        self.target_keyboard_btn.clicked.connect(lambda: self.set_color_target("keyboard"))
        
        target_layout.addWidget(self.target_mouse_btn)
        target_layout.addWidget(self.target_keyboard_btn)
        card_layout.addLayout(target_layout)

        self.update_target_button_styles()

        card_layout.addSpacing(10)
        self.bright_label = QLabel("Brightness: <b>100%</b>")
        card_layout.addWidget(self.bright_label)
        
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setMinimum(0)
        self.bright_slider.setMaximum(100)
        self.bright_slider.setValue(100)
        self.bright_slider.valueChanged.connect(self.on_brightness_changed)
        card_layout.addWidget(self.bright_slider)

        self.breathe_container = QWidget()
        breathe_layout = QVBoxLayout(self.breathe_container)
        breathe_layout.setContentsMargins(0, 5, 0, 0)
        
        self.breathe_range_label = QLabel("Breathe Range: Min <b>10%</b> — Max <b>100%</b>")
        breathe_layout.addWidget(self.breathe_range_label)
        
        breathe_sliders_layout = QHBoxLayout()
        self.breathe_min_slider = QSlider(Qt.Orientation.Horizontal)
        self.breathe_min_slider.setMinimum(0)
        self.breathe_min_slider.setMaximum(100)
        self.breathe_min_slider.setValue(10)
        self.breathe_min_slider.valueChanged.connect(self.on_breathe_range_changed)
        
        self.breathe_max_slider = QSlider(Qt.Orientation.Horizontal)
        self.breathe_max_slider.setMinimum(0)
        self.breathe_max_slider.setMaximum(100)
        self.breathe_max_slider.setValue(100)
        self.breathe_max_slider.valueChanged.connect(self.on_breathe_range_changed)
        
        breathe_sliders_layout.addWidget(QLabel("Min:"))
        breathe_sliders_layout.addWidget(self.breathe_min_slider)
        breathe_sliders_layout.addWidget(QLabel("Max:"))
        breathe_sliders_layout.addWidget(self.breathe_max_slider)
        breathe_layout.addLayout(breathe_sliders_layout)

        breathe_layout.addSpacing(5)
        self.breathe_speed_label = QLabel("Breathe Speed: <b>Medium</b>")
        breathe_layout.addWidget(self.breathe_speed_label)
        
        self.breathe_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.breathe_speed_slider.setMinimum(1)
        self.breathe_speed_slider.setMaximum(3)
        self.breathe_speed_slider.setValue(2)
        self.breathe_speed_slider.valueChanged.connect(self.on_breathe_speed_changed)
        breathe_layout.addWidget(self.breathe_speed_slider)
        
        self.breathe_container.hide()
        card_layout.addWidget(self.breathe_container)

        card_layout.addSpacing(10)
        card_layout.addWidget(QLabel("<b>EFFECT MODE</b>"))
        
        effect_layout = QHBoxLayout()
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(["Static (Custom Color)", "Breathe"])
        self.effect_combo.currentIndexChanged.connect(self.on_effect_mode_changed)
        effect_layout.addWidget(self.effect_combo)
        effect_layout.addStretch()
        card_layout.addLayout(effect_layout)

        card_layout.addSpacing(10)
        card_layout.addWidget(QLabel("<b>16M COLOR SPECTRUM GAMUT & HEX INPUT</b>"))

        top_bar = QHBoxLayout()
        self.color_preview_lbl = QLabel()
        self.color_preview_lbl.setFixedSize(40, 28)
        self.color_preview_lbl.setStyleSheet("background-color: #00ff00; border: 1px solid #555555; border-radius: 4px;")
        top_bar.addWidget(self.color_preview_lbl)

        top_bar.addWidget(QLabel("Hex Code:"))
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("#00ff00")
        self.hex_input.setText("#00ff00")
        self.hex_input.setFixedWidth(110)
        self.hex_input.returnPressed.connect(self.apply_color_from_hex)
        top_bar.addWidget(self.hex_input)

        apply_hex_btn = QPushButton("Apply Hex")
        apply_hex_btn.clicked.connect(self.apply_color_from_hex)
        top_bar.addWidget(apply_hex_btn)
        top_bar.addStretch()
        card_layout.addLayout(top_bar)

        self.spectrum_widget = GamutSpectrumWidget()
        self.spectrum_widget.colorSelected.connect(self.on_spectrum_color_picked)
        card_layout.addWidget(self.spectrum_widget)

        card_layout.addStretch()
        layout.addWidget(card)
        return tab

    def set_color_target(self, target):
        self.current_target = target
        self.target_mouse_btn.setChecked(target == "mouse")
        self.target_keyboard_btn.setChecked(target == "keyboard")
        self.update_target_button_styles()
        
        self.effect_combo.blockSignals(True)
        if target == "mouse":
            self.effect_combo.clear()
            self.effect_combo.addItem("Static (Custom Color)")
            self.effect_combo.setEnabled(False)
        else:
            self.effect_combo.setEnabled(True)
            self.effect_combo.clear()
            self.effect_combo.addItems(["Static (Custom Color)", "Breathe"])
        self.effect_combo.blockSignals(False)

        self.refresh_lighting_ui_from_state()

    def update_target_button_styles(self):
        active_style = "background-color: #00ff00; color: #000000; font-weight: bold; border: none;"
        inactive_style = "background-color: #222222; color: #ffffff; border: 1px solid #3a3a3a;"
        
        if self.current_target == "mouse":
            self.target_mouse_btn.setStyleSheet(active_style)
            self.target_keyboard_btn.setStyleSheet(inactive_style)
        else:
            self.target_mouse_btn.setStyleSheet(inactive_style)
            self.target_keyboard_btn.setStyleSheet(active_style)

    def refresh_lighting_ui_from_state(self):
        st = self.device_states[self.current_target]
        
        self.effect_combo.blockSignals(True)
        self.bright_slider.blockSignals(True)
        self.breathe_min_slider.blockSignals(True)
        self.breathe_max_slider.blockSignals(True)
        self.breathe_speed_slider.blockSignals(True)
        self.hex_input.blockSignals(True)

        if self.current_target == "keyboard":
            self.effect_combo.setCurrentText(st["effect"])
        else:
            self.effect_combo.setCurrentText("Static (Custom Color)")
        
        is_breathe = (st["effect"] == "Breathe" and self.current_target == "keyboard")
        if is_breathe:
            self.bright_slider.hide()
            self.bright_label.hide()
            self.breathe_container.show()
        else:
            self.breathe_container.hide()
            self.bright_slider.show()
            self.bright_label.show()

        self.bright_slider.setValue(st["brightness"])
        self.bright_label.setText(f"Brightness: <b>{st['brightness']}%</b>")

        self.breathe_min_slider.setValue(st["breathe_min"])
        self.breathe_max_slider.setValue(st["breathe_max"])
        self.breathe_range_label.setText(f"Breathe Range: Min <b>{st['breathe_min']}%</b> — Max <b>{st['breathe_max']}%</b>")

        self.breathe_speed_slider.setValue(st["breathe_speed"])
        speed_names = {1: "Slow", 2: "Medium", 3: "Fast"}
        self.breathe_speed_label.setText(f"Breathe Speed: <b>{speed_names.get(st['breathe_speed'], 'Medium')}</b>")

        hex_str = st["color"].name()
        self.hex_input.setText(hex_str)
        self.color_preview_lbl.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #555555; border-radius: 4px;")

        self.effect_combo.blockSignals(False)
        self.bright_slider.blockSignals(False)
        self.breathe_min_slider.blockSignals(False)
        self.breathe_max_slider.blockSignals(False)
        self.breathe_speed_slider.blockSignals(False)
        self.hex_input.blockSignals(False)

    def on_spectrum_color_picked(self, col: QColor):
        st = self.device_states[self.current_target]
        st["color"] = col
        hex_str = col.name()
        
        self.hex_input.blockSignals(True)
        self.hex_input.setText(hex_str)
        self.hex_input.blockSignals(False)

        self.color_preview_lbl.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #555555; border-radius: 4px;")
        self.apply_static_color_to_device(self.current_target, col.red(), col.green(), col.blue())

    def apply_color_from_hex(self):
        text = self.hex_input.text().strip()
        if not text.startswith("#"):
            text = "#" + text
            
        col = QColor(text)
        if col.isValid():
            st = self.device_states[self.current_target]
            st["color"] = col
            hex_str = col.name()
            r, g, b = col.red(), col.green(), col.blue()

            self.color_preview_lbl.setStyleSheet(f"background-color: {hex_str}; border: 1px solid #555555; border-radius: 4px;")
            self.apply_static_color_to_device(self.current_target, r, g, b)
        else:
            QMessageBox.warning(self, "Invalid Hex", f"Could not parse '{text}' as a valid hex color code. Use format #ff0000.")

    def apply_static_color_to_device(self, target, r, g, b):
        self.razer.set_static(target, r, g, b)

    def on_effect_mode_changed(self, index):
        effect_name = self.effect_combo.currentText()
        st = self.device_states[self.current_target]
        st["effect"] = effect_name
        is_breathe = (effect_name == "Breathe")

        if self.current_target == "mouse" and is_breathe:
            self.effect_combo.blockSignals(True)
            self.effect_combo.setCurrentText("Static (Custom Color)")
            self.effect_combo.blockSignals(False)
            st["effect"] = "Static (Custom Color)"
            is_breathe = False

        col = st["color"]
        if is_breathe:
            self.bright_slider.hide()
            self.bright_label.hide()
            self.breathe_container.show()
            st["breathe_val"] = st["breathe_min"]
            self.razer.set_static(self.current_target, col.red(), col.green(), col.blue())
        else:
            self.breathe_container.hide()
            self.bright_slider.show()
            self.bright_label.show()
            self.razer.set_static(self.current_target, col.red(), col.green(), col.blue())
            self.razer.set_brightness(self.current_target, st["brightness"])

    def on_breathe_range_changed(self):
        min_val = self.breathe_min_slider.value()
        max_val = self.breathe_max_slider.value()
        if min_val > max_val:
            min_val = max_val
            self.breathe_min_slider.setValue(min_val)
        
        st = self.device_states[self.current_target]
        st["breathe_min"] = min_val
        st["breathe_max"] = max_val
        self.breathe_range_label.setText(f"Breathe Range: Min <b>{min_val}%</b> — Max <b>{max_val}%</b>")

    def on_breathe_speed_changed(self, value):
        speed_names = {1: "Slow", 2: "Medium", 3: "Fast"}
        self.breathe_speed_label.setText(f"Breathe Speed: <b>{speed_names.get(value, 'Medium')}</b>")
        st = self.device_states[self.current_target]
        st["breathe_speed"] = value

    def run_independent_breathe_steps(self):
        st = self.device_states["keyboard"]
        if st["effect"] != "Breathe":
            return
        min_val = st["breathe_min"]
        max_val = st["breathe_max"]
        if min_val >= max_val:
            max_val = min_val + 1

        speed = st["breathe_speed"]
        step = 1 if speed == 1 else (2 if speed == 2 else 4)

        st["breathe_val"] += st["breathe_dir"] * step
        if st["breathe_val"] >= max_val:
            st["breathe_val"] = max_val
            st["breathe_dir"] = -1
        elif st["breathe_val"] <= min_val:
            st["breathe_val"] = min_val
            st["breathe_dir"] = 1

        value = int(st["breathe_val"])
        if value != st.get("_last_sent"):
            st["_last_sent"] = value
            self.razer.set_brightness("keyboard", value)

    def on_brightness_changed(self, value):
        self.bright_label.setText(f"Brightness: <b>{value}%</b>")
        self.device_states[self.current_target]["brightness"] = value
        self.razer.set_brightness(self.current_target, value)

    def handle_mouse_function_selection(self, index):
        if index > 0:
            selected_func = self.mouse_func_combo.currentText()
            self.key_input.setText(selected_func)
            self.save_current_binding()

    def update_detected_hardware_labels(self):
        import html
        kb_name = self.razer.name('keyboard')
        mouse_name = self.razer.name('mouse')
        
        self.keyboard_lbl.setText(f"<b>Keyboard:</b> {html.escape(kb_name)}")
        mouse_text = f"<b>Mouse:</b> {html.escape(mouse_name)}"
        if self.razer.error:
            mouse_text += f" &nbsp;&nbsp;|&nbsp;&nbsp; <span style='color:#ff6666;'>{html.escape(self.razer.error)}</span>"
        self.mouse_lbl.setText(mouse_text)

        kb_image_path = get_cached_device_image(kb_name, None, fallback="keyboard_default")
        if kb_image_path and os.path.exists(kb_image_path):
            self.keyboard_icon_lbl.setPixmap(QPixmap(kb_image_path).scaled(50, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

        mouse_image_path = get_cached_device_image(mouse_name, None, fallback="mouse_default")
        if mouse_image_path and os.path.exists(mouse_image_path):
            self.mouse_icon_lbl.setPixmap(QPixmap(mouse_image_path).scaled(50, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def set_panel_view(self, panel_type):
        self.current_active_panel = panel_type
        for k, btn in self.thumb_buttons.items():
            if k == panel_type:
                btn.setStyleSheet("QPushButton { background-color: #1e1e1e; color: #00ff00; border: 2px solid #00ff00; font-weight: bold; border-radius: 6px; }")
            else:
                btn.setStyleSheet("QPushButton { background-color: #222222; color: #888888; border: 1px solid #3a3a3a; font-weight: bold; border-radius: 6px; } QPushButton:hover { border: 1px solid #00ff00; color: #ffffff; }")
        self.update_ui_layout(panel_type)

    def update_ui_layout(self, panel_type):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout:
                    while sub_layout.count():
                        sub_item = sub_layout.takeAt(0)
                        sub_widget = sub_item.widget()
                        if sub_widget:
                            sub_widget.deleteLater()

        if panel_type == "top":
            new_layout = self.build_top_buttons_layout()
            self.container_layout.addLayout(new_layout)
        elif panel_type == "12-button" and self.is_mmo_mouse:
            new_grid = self.build_12_button_grid()
            self.container_layout.addLayout(new_grid)
        elif panel_type == "7-button" and self.is_mmo_mouse:
            new_grid = self.build_7_button_layout()
            self.container_layout.addLayout(new_grid)
        elif panel_type == "2-button" or not self.is_mmo_mouse:
            new_layout = self.build_2_button_layout()
            self.container_layout.addLayout(new_layout)

    def build_top_buttons_layout(self):
        main_top_layout = QHBoxLayout()
        main_top_layout.setContentsMargins(0, 0, 0, 0)
        main_top_layout.setSpacing(10)
        main_top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hw_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        btn_left = QPushButton("Scroll\nLeft")
        btn_left.setCheckable(True)
        btn_left.setFixedSize(65, 65)
        main_top_layout.addWidget(btn_left, alignment=Qt.AlignmentFlag.AlignCenter)
        self.hw_buttons["Scroll_Left"] = btn_left
        self.button_group.addButton(btn_left)
        btn_left.clicked.connect(lambda checked, n="Scroll_Left": self.on_hardware_button_clicked(n))

        middle_stack = QWidget()
        middle_layout = QVBoxLayout(middle_stack)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(6)
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        middle_specs = [
            ("Top Scroll Forward", "Top_Forward"),
            ("Top Wheel Click", "Top_M"),
            ("Top Scroll Back", "Top_Back")
        ]

        for text, name in middle_specs:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedWidth(150)
            btn.setFixedHeight(38)
            middle_layout.addWidget(btn)
            self.hw_buttons[name] = btn
            self.button_group.addButton(btn)
            btn.clicked.connect(lambda checked, n=name: self.on_hardware_button_clicked(n))

        main_top_layout.addWidget(middle_stack, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_right = QPushButton("Scroll\nRight")
        btn_right.setCheckable(True)
        btn_right.setFixedSize(65, 65)
        main_top_layout.addWidget(btn_right, alignment=Qt.AlignmentFlag.AlignCenter)
        self.hw_buttons["Scroll_Right"] = btn_right
        self.button_group.addButton(btn_right)
        btn_right.clicked.connect(lambda checked, n="Scroll_Right": self.on_hardware_button_clicked(n))

        self.update_button_visuals()
        return main_top_layout

    def build_12_button_grid(self):
        grid_layout = QGridLayout()
        self.hw_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        mapping = [
            ('3', 0, 0), ('6', 0, 1), ('9', 0, 2), ('12', 0, 3),
            ('2', 1, 0), ('5', 1, 1), ('8', 1, 2), ('11', 1, 3),
            ('1', 2, 0), ('4', 2, 1), ('7', 2, 2), ('10', 2, 3)
        ]
        for name, r, c in mapping:
            btn = QPushButton(name)
            btn.setFixedSize(55, 55)
            btn.setCheckable(True)
            grid_layout.addWidget(btn, r, c)
            self.hw_buttons[name] = btn
            self.button_group.addButton(btn)
            btn.clicked.connect(lambda checked, n=name: self.on_hardware_button_clicked(n))
        
        self.update_button_visuals()
        return grid_layout

    def build_7_button_layout(self):
        grid_layout = QGridLayout()
        self.hw_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        mapping = [
            ('2', 0, 0), ('3', 0, 1), 
            ('1', 1, 0),             ('7', 1, 2), 
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2)
        ]
        
        for name, r, c in mapping:
            btn = QPushButton(name)
            btn.setFixedSize(55, 55)
            btn.setCheckable(True)
            grid_layout.addWidget(btn, r, c)
            self.hw_buttons[name] = btn
            self.button_group.addButton(btn)
            btn.clicked.connect(lambda checked, n=name: self.on_hardware_button_clicked(n))
        
        center_spacer = QLabel()
        center_spacer.setFixedSize(55, 55)
        center_spacer.setStyleSheet("background-color: #141414; border: 1px dashed #333333; border-radius: 27px;")
        grid_layout.addWidget(center_spacer, 1, 1)

        self.update_button_visuals()
        return grid_layout

    def build_2_button_layout(self):
        layout = QVBoxLayout()
        self.hw_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        buttons_data = [("Side (Back)", "Side"), ("Extra (Forward)", "Extra")]
        for text, name in buttons_data:
            btn = QPushButton(text)
            btn.setFixedHeight(45)
            btn.setCheckable(True)
            layout.addWidget(btn)
            self.hw_buttons[name] = btn
            self.button_group.addButton(btn)
            btn.clicked.connect(lambda checked, n=name: self.on_hardware_button_clicked(n))

        self.update_button_visuals()
        return layout

    def get_active_bindings(self):
        curr_prof = self.get_active_profile_name()
        prof_data = self.profiles.get(curr_prof, {})
        
        if isinstance(prof_data, dict):
            if "bindings" in prof_data:
                return prof_data["bindings"]
            return prof_data
        return {}

    def update_button_visuals(self):
        current_bindings = self.get_active_bindings()
        
        for name, btn in self.hw_buttons.items():
            is_selected = (name == self.active_button_name)
            binding_val = current_bindings.get(name, "")
            has_binding = bool(binding_val and str(binding_val).strip())
            
            btn.setProperty("has_binding", has_binding)
            
            if is_selected:
                if has_binding:
                    btn.setStyleSheet("background-color: #00ff00; color: #000000; border: 3px solid #ffff00; font-weight: bold; border-radius: 6px;")
                else:
                    btn.setStyleSheet("background-color: #1f1f1f; color: #00ff00; border: 3px solid #ffff00; font-weight: bold; border-radius: 6px;")
            elif has_binding:
                btn.setStyleSheet("background-color: #00ff00; color: #000000; border: 1px solid #00ff00; font-weight: bold; border-radius: 6px;")
            else:
                btn.setStyleSheet("background-color: #1f1f1f; color: #00ff00; border: 1px solid #00ff00; font-weight: bold; border-radius: 6px;")

    def on_hardware_button_clicked(self, button_name):
        self.save_current_binding()
        self.active_button_name = button_name
        self.target_label.setText(f"Configuring: <b>{button_name}</b>")
        
        current_bindings = self.get_active_bindings()
        val = current_bindings.get(button_name, "")
        self.key_input.setText(val)
        
        self.mouse_func_combo.blockSignals(True)
        if val in ["Left Click", "Right Click", "Middle Click", "Back", "Forward", "Scroll Up", "Scroll Down", "Scroll Left", "Scroll Right"]:
            self.mouse_func_combo.setCurrentText(val)
        else:
            self.mouse_func_combo.setCurrentIndex(0)
        self.mouse_func_combo.blockSignals(False)
        
        self.update_button_visuals()

    def save_current_binding(self):
        if self.active_button_name:
            curr_prof = self.get_active_profile_name()
            if curr_prof in self.profiles:
                if isinstance(self.profiles[curr_prof], dict) and "bindings" in self.profiles[curr_prof]:
                    self.profiles[curr_prof]["bindings"][self.active_button_name] = self.key_input.text()
                else:
                    self.profiles[curr_prof][self.active_button_name] = self.key_input.text()
                self.update_button_visuals()

    def start_recording(self, button_name):
        self.is_recording = True
        self.active_button_name = button_name
        self.setFocus()
        self.key_input.clear()

    def keyPressEvent(self, event):
        if self.is_recording and self.active_button_name:
            if event.isAutoRepeat(): 
                return
            key = event.key()
            modifiers = event.modifiers()
            scancode = event.nativeScanCode()
            
            combo_parts = []

            if modifiers & Qt.KeyboardModifier.ControlModifier or key == Qt.Key.Key_Control:
                combo_parts.append("Ctrl")
            if modifiers & Qt.KeyboardModifier.ShiftModifier or key == Qt.Key.Key_Shift:
                combo_parts.append("Shift")
            if modifiers & Qt.KeyboardModifier.AltModifier or key == Qt.Key.Key_Alt:
                combo_parts.append("Alt")

            is_modifier_key = key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt]

            if not is_modifier_key and not (len(combo_parts) > 0 and key in [16777249, 16777248]):
                is_numpad = bool(modifiers & Qt.KeyboardModifier.KeypadModifier)
                scancode_num_map = {10: "1", 11: "2", 12: "3", 13: "4", 14: "5", 15: "6", 16: "7", 17: "8", 18: "9", 19: "0"}
                if scancode in scancode_num_map and not is_numpad:
                    combo_parts.append(scancode_num_map[scancode])
                elif is_numpad and (key == Qt.Key.Key_Slash or event.text() == "/"):
                    combo_parts.append("KP_Divide")
                elif key == Qt.Key.Key_Slash or event.text() == "/":
                    combo_parts.append("slash")
                elif key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z:
                    combo_parts.append(chr(key))
                elif key >= Qt.Key.Key_F1 and key <= Qt.Key.Key_F12:
                    combo_parts.append(f"F{key - Qt.Key.Key_F1 + 1}")
                elif event.text():
                    combo_parts.append(event.text().upper())

            final_parts = []
            for part in combo_parts:
                if part not in final_parts: 
                    final_parts.append(part)
            if final_parts:
                self.key_input.setText("+".join(final_parts))

    def keyReleaseEvent(self, event):
        if self.is_recording and self.active_button_name:
            if event.isAutoRepeat(): return
            self.save_current_binding()
            self.toggle_key_recording()

    def toggle_key_recording(self):
        if not self.active_button_name: return
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.current_combo.clear()
            self.record_btn.setText("Hold layout keys...")
            self.setFocus()
        else:
            self.record_btn.setText("Record Keyboard Function")

    def get_profile_names(self):
        return list(self.profiles.keys())

    def get_active_profile_name(self):
        if self.profile_dropdowns:
            return self.profile_dropdowns[0].currentText()
        return "Default Profile"

    def sync_all_profile_dropdowns(self, profile_name):
        for combo in self.profile_dropdowns:
            combo.blockSignals(True)
            combo.setCurrentText(profile_name)
            combo.blockSignals(False)
        self.update_tray_profile_menu()

    def handle_dropdown_profile_change(self, index):
        sender_combo = self.sender()
        if sender_combo:
            prof_name = sender_combo.currentText()
            self.sync_all_profile_dropdowns(prof_name)
            self.change_profile(0)

    def register_active_alias(self, profile_name, new_identifier):
        if not new_identifier or profile_name not in self.profiles:
            return False

        profile_data = self.profiles[profile_name]
        if not isinstance(profile_data, dict):
            return False

        aliases = profile_data.setdefault("aliases", [])
        normalized_aliases = [a.lower().strip() for a in aliases]
        clean_id = new_identifier.lower().strip()

        if clean_id not in normalized_aliases:
            aliases.append(clean_id)
            self.save_profiles_to_disk_silent()
            logger.info(f"Auto-registered new alias '{clean_id}' for profile '{profile_name}'")
            return True
        return False

    def save_profiles_to_disk_silent(self):
        try:
            os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
            with open(PROFILE_FILE, 'w') as f:
                json.dump(self.profiles, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save profiles quietly: {e}")

    def handle_auto_window_switch(self, window_info):
        win_id, class_tokens, window_title = window_info
        matched_profile = None
        matched_token = None

        for p in self.profiles.keys():
            p_lower = p.lower()
            prof_data = self.profiles[p]
            aliases = prof_data.get("aliases", []) if isinstance(prof_data, dict) else []
            if not aliases:
                aliases = [p_lower.replace(" ", "") + ".exe", p_lower]
            
            match_found = any(any(alias.lower() in token for token in class_tokens) for alias in aliases) or \
                          any(alias.lower() in window_title for alias in aliases)
            
            if not match_found and "pso2" in p_lower and ("pso2" in window_title or any("pso2" in t for t in class_tokens)):
                match_found = True

            if match_found:
                matched_profile = p
                break

        if not matched_profile:
            for token in class_tokens:
                if token.startswith("steam_app_"):
                    current_selected = self.get_active_profile_name()
                    if current_selected != "Default Profile":
                        matched_profile = current_selected
                        matched_token = token
                        break

        if matched_profile:
            current_selected = self.get_active_profile_name()
            if current_selected != matched_profile:
                self.sync_all_profile_dropdowns(matched_profile)
                self.change_profile(0)
            
            if matched_token:
                self.register_active_alias(matched_profile, matched_token)
            elif window_title and len(window_title) > 3:
                if matched_profile != "Default Profile":
                    self.register_active_alias(matched_profile, window_title)

    def load_profiles(self):
        default_blueprints = {
            "Default Profile": {"bindings": {}, "dpi": 1800, "aliases": ["default"]}, 
            "ffxiv": {"bindings": {"1": "Ctrl+1"}, "dpi": 3600, "aliases": ["ffxivgame.x64", "ffxiv.exe", "ffxiv", "final fantasy xiv", "final fantasy 14"]}, 
            "PSO2 NGS": {"bindings": {"1": "X", "2": "Shift", "3": "Middle Click", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "0", "11": "-", "12": "="}, "dpi": 4800, "aliases": ["pso2.exe", "pso2_bin/pso2.exe", "phantasy star online 2 new genesis", "new genesis"]}
        }
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, 'r') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if isinstance(v, dict):
                            if "bindings" not in v:
                                data[k] = {"bindings": v, "dpi": 1800}
                            
                            base = k.lower().replace(" ", "")
                            if "pso2" in base:
                                data[k]["aliases"] = ["pso2.exe", "pso2_bin/pso2.exe", "phantasy star online 2 new genesis", "new genesis"]
                            elif "ffxiv" in base or "finalfantasy" in base:
                                data[k]["aliases"] = ["ffxivgame.x64", "ffxiv.exe", "ffxiv", "final fantasy xiv", "final fantasy 14"]
                            elif "aliases" not in data[k]:
                                data[k]["aliases"] = [base + ".exe", base, k.lower()]
                    return data
            except Exception as e:
                logger.error(f"Failed to load profiles from disk: {e}")
        return default_blueprints

    def save_to_disk(self):
        self.save_current_binding()
        
        for profile_name, profile_data in self.profiles.items():
            if isinstance(profile_data, dict):
                base = profile_name.lower().replace(" ", "")
                if "pso2" in base:
                    profile_data["aliases"] = ["pso2.exe", "pso2_bin/pso2.exe", "phantasy star online 2 new genesis", "new genesis"]
                elif "ffxiv" in base or "finalfantasy" in base:
                    profile_data["aliases"] = ["ffxivgame.x64", "ffxiv.exe", "ffxiv", "final fantasy xiv", "final fantasy 14"]
                elif "aliases" not in profile_data:
                    profile_data["aliases"] = [base + ".exe", base, profile_name.lower()]

        os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
        with open(PROFILE_FILE, 'w') as f:
            json.dump(self.profiles, f, indent=4)
        self.update_button_visuals()
        self.update_tray_profile_menu()
        QMessageBox.information(self, "Success", "Layout profiles and DPI settings successfully updated.")

    def change_profile(self, index):
        profile_name = self.get_active_profile_name()
        if not profile_name: return
        
        self.sync_all_profile_dropdowns(profile_name)
        
        self.active_button_name = None
        self.key_input.clear()
        self.mouse_func_combo.setCurrentIndex(0)
        self.update_button_visuals()

        prof_data = self.profiles.get(profile_name, {})
        if isinstance(prof_data, dict) and "dpi" in prof_data:
            target_dpi = prof_data["dpi"]
            self.dpi_slider.blockSignals(True)
            self.dpi_slider.setValue(target_dpi)
            self.dpi_slider.blockSignals(False)
            self.dpi_label.setText(f"Current DPI: <b>{target_dpi}</b> (Profile Preset)")
            self._apply_hw_dpi(target_dpi)

    def create_profile(self):
        text, ok = QInputDialog.getText(self, 'New Profile', 'Enter name:')
        if ok and text.strip() and text.strip() not in self.profiles:
            new_name = text.strip()
            self.profiles[new_name] = {"bindings": {}, "dpi": 1800}
            
            for combo in self.profile_dropdowns:
                combo.blockSignals(True)
                combo.addItem(new_name)
                combo.setCurrentText(new_name)
                combo.blockSignals(False)
            
            self.update_tray_profile_menu()
            self.change_profile(0)

    def remove_profile_file(self, profile_name):
        profile_path = os.path.expanduser(f"~/.config/openchroma/{profile_name}.json")
        if os.path.exists(profile_path):
            os.remove(profile_path)
            logger.info(f"Removed profile file: {profile_path}")

    def delete_profile(self):
        current_prof = self.get_active_profile_name()
        if not current_prof or current_prof == "Default Profile":
            QMessageBox.warning(self, "Warning", "Cannot delete the Default Profile or an empty selection.")
            return

        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Are you sure you want to delete profile '{current_prof}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if current_prof in self.profiles:
                    del self.profiles[current_prof]
                
                self.remove_profile_file(current_prof)
                
                for combo in self.profile_dropdowns:
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItems(self.get_profile_names())
                    combo.blockSignals(False)
                
                self.update_tray_profile_menu()
                self.change_profile(0)
                self.save_to_disk()
                
                QMessageBox.information(self, "Success", f"Profile '{current_prof}' was successfully deleted.")
            except Exception as e:
                logger.error(f"Failed to delete profile: {e}")
                QMessageBox.critical(self, "Error", f"Could not delete profile: {e}")

    def export_profiles(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Profiles", os.path.expanduser("~/naga_profiles_backup.json"), "JSON Files (*.json)")
        if file_path:
            try:
                self.save_current_binding()
                with open(file_path, 'w') as f:
                    json.dump(self.profiles, f, indent=4)
                QMessageBox.information(self, "Success", f"Profiles successfully exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export profiles: {e}")

    def import_profiles(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Profiles", os.path.expanduser("~"), "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    imported_data = json.load(f)
                if isinstance(imported_data, dict) and imported_data:
                    self.profiles = imported_data
                    for combo in self.profile_dropdowns:
                        combo.blockSignals(True)
                        combo.clear()
                        combo.addItems(self.get_profile_names())
                        combo.blockSignals(False)
                    self.update_tray_profile_menu()
                    self.change_profile(0)
                    self.save_to_disk()
                    QMessageBox.information(self, "Success", "Profiles successfully imported and applied!")
                else:
                    QMessageBox.warning(self, "Invalid File", "The selected file does not contain a valid profile dictionary.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import profiles: {e}")

if __name__ == '__main__':
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    app = QApplication(sys.argv)
    app.setApplicationName("OpenChroma")
    app.setDesktopFileName("openchroma")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "assets", "OpenChroma.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    ex = NagaSynapseApp()
    ex.show()
    sys.exit(app.exec())