from typing import Optional

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Signal
from lib.device.joystick import JoystickManager
from console.core.active_joystick import ActiveJoystick
from console.core.comms.stm32 import STM32
from console.core.comms.comms import CommunicationManager
from console.gui.main_window import MainWindow

from console.gui.splash_screen import LoadingSplash

import sys
from pathlib import Path
import os

# os.environ["QT_QPA_PLATFORM"] = "xcb"
# os.environ["QT_QUICK_BACKEND"] = "software"
current_file = Path(__file__).resolve()

if getattr(sys, "frozen", False):
    # BUNDLE: /dist/ROV-Console/_internal/ (onedir) or /tmp/_MEIxxx (onefile)
    root = Path(sys._MEIPASS)
    lib_folder = root / "bin"
else:
    # DEV: Assuming structure is project/src/console/__main__.py
    # and bin is at project/bin/linux_x64
    # We go up from __main__.py (1) -> console (2) -> src (3) -> project_root
    root = current_file.parent.parent.parent
    lib_folder = root / "bin" / "linux_x64"

# CRITICAL: Verification
if not lib_folder.exists():
    print(f"DEBUG: Path fail! Search dir {lib_folder} does not exist.")
    # Fallback to current working directory if parent logic fails
    lib_folder = Path(os.getcwd()) / "bin" / "linux_x64"

lib_path = str(lib_folder.absolute())

# Set Environment
os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"
os.environ["GST_PLUGIN_PATH"] = str(lib_folder / "gstreamer-1.0")
os.environ["GST_PLUGIN_SCANNER"] = str(lib_folder / "helpers" / "gst-plugin-scanner")

# Fix: Move registry to a writable temp location to avoid permission errors
os.environ["GST_REGISTRY"] = f"/tmp/gst_registry_{os.getpid()}.bin"

# If dev still fails, comment this out to let it use system plugins as a backup
os.environ["GST_PLUGIN_SYSTEM_PATH"] = ""


class ConsoleApplication(QApplication):
    startup_progress = Signal(str, int)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._splash_screen: Optional[LoadingSplash] = None
        self._joystick_manager: Optional[JoystickManager]
        self._active_joystick = ActiveJoystick()
        self._serial_device: Optional[STM32] = None
        self._comms_manager: Optional[CommunicationManager] = None
        self._main_window: Optional[QMainWindow] = None
        self.aboutToQuit.connect(self._shutdown)
        self._startup()

    def _startup(self):
        self._splash_screen = LoadingSplash()
        self._splash_screen.show()
        self._splash_screen.update_progress("Initializing joystick system", 20)
        self._joystick_manager = JoystickManager()
        joysticks = self._joystick_manager.joysticks
        if len(joysticks) > 0:
            self._active_joystick.selected = joysticks[0]
        self._splash_screen.update_progress("Initializing serial system", 40)
        self._serial_device = STM32(115200)
        self._splash_screen.update_progress("Initializing communication system", 60)
        self._comms_manager = CommunicationManager(self._serial_device, self._active_joystick)
        self._splash_screen.update_progress("Starting GUI", 80)
        self._main_window = MainWindow(
            self._serial_device, self._active_joystick, self._comms_manager
        )
        self._splash_screen.hide()
        self._splash_screen = None
        self._main_window.show()

    def _shutdown(self):
        self._main_window = None
        if self._comms_manager is not None:
            self._comms_manager._killswitch = True
        self._active_joystick.selected = None
        if self._joystick_manager is not None:
            self._joystick_manager.shutdown()
        if self._serial_device is not None:
            self._serial_device.disconnect()


def run():
    import sys

    sys.exit(ConsoleApplication().exec())


if __name__ == "__main__":
    run()
