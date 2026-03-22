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

if getattr(sys, 'frozen', False):
    # PyInstaller extracts everything to a temp folder stored in _MEIPASS
    base_dir = Path(sys._MEIPASS)
    bin_dir = base_dir / "bin" / "linux_x64"
else:
    # Normal development mode
    base_dir = Path(__file__).resolve().parent.parent.parent
    bin_dir = base_dir / "bin" / "linux_x64"

if bin_dir.exists():
    os.environ["LD_LIBRARY_PATH"] = f"{bin_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"

    # 2. GStreamer Environment
    os.environ["GST_PLUGIN_PATH"] = str(bin_dir / "gstreamer-1.0")
    os.environ["GST_PLUGIN_SCANNER"] = str(bin_dir / "helpers" / "gst-plugin-scanner")

# Put the registry in the user's config folder so it's persistent/writable
# (The bundle folder itself is read-only)
user_data = Path(os.path.expanduser("~/.local/share/ROV26"))
user_data.mkdir(parents=True, exist_ok=True)
os.environ["GST_REGISTRY"] = str(user_data / "registry.bin")


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
        # self._comms_manager = CommunicationManager(self._serial_device, self._active_joystick)
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
