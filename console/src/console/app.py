from typing import Optional

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Signal
from console.comms.stm32 import Stm32
from console.env import Settings
from hal.joystick.manager import JoystickManager
from hal.joystick.active_joystick import ActiveJoystick
from console.comms.manager import CommunicationManager
from console.gui.main_window import MainWindow
from console.gui.splash_screen import LoadingSplash


class ConsoleApplication(QApplication):
    startup_progress = Signal(str, int)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.splash_screen: Optional[LoadingSplash] = None
        self.joystick_manager: Optional[JoystickManager]
        self.active_joystick = ActiveJoystick()
        self.stm32: Optional[Stm32] = None
        self.comms_manager: Optional[CommunicationManager] = None
        self.main_window: Optional[QMainWindow] = None
        self.aboutToQuit.connect(self.shutdown)
        self.startup()

    def startup(self):
        self.splash_screen = LoadingSplash()
        self.splash_screen.show()

        self.splash_screen.update_progress("Initializing joystick system", 20)
        self.joystick_manager = JoystickManager()

        
        self.splash_screen.update_progress("Initializing serial system", 40)
        self.stm32 = Stm32()

        self.splash_screen.update_progress("Initializing communication system", 60)
        self.comms_manager = CommunicationManager(self.stm32, self.active_joystick)

        self.splash_screen.update_progress("Starting GUI", 80)
        self.main_window = MainWindow(
            self.stm32, self.active_joystick, self.comms_manager
        )
        
        self.splash_screen.update_progress("Loading user settings", 100)
        settings = Settings()

        self.splash_screen.hide()
        self.splash_screen = None
        self.main_window.show()
        if settings.is_fresh:
            self.main_window.initial_setup()

    def shutdown(self):
        self.main_window = None
        if self.comms_manager is not None:
            self.comms_manager._killswitch = True
        self.active_joystick.selected = None
        if self.joystick_manager is not None:
            self.joystick_manager.shutdown()
        if self.stm32 is not None:
            self.stm32.port = None


def start_console():
    import sys

    sys.exit(ConsoleApplication().exec())
