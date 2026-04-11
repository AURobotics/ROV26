from typing import Optional

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Signal
from hal.joystick.manager import JoystickManager
from hal.joystick.active_joystick import ActiveJoystick
from hal.serial.stm32 import STM32
from console.comms.comms.comms import CommunicationManager
from console.gui.main_window import MainWindow

from console.gui.splash_screen import LoadingSplash

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
