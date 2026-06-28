"""
Wrapper for PyGame joysticks.
Manages the following:
   - Choosing one or none of the currently connected gamepads
   - Regularly checking for, presenting and managing connection changes
   - Providing an event-based interface for tracking
"""

from hal.joystick.manager import JoystickManager
