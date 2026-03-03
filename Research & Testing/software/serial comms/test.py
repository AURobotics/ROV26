"""
Test script for CommunicationManager
Run from ROV26\ directory:
    python console/test_comms.py
"""

import time
import sys
sys.path.insert(0, r"D:\mohab\AUR\AUR-Team\ROV'26\ROV26\console\src")

from console.core.gamepad.gamepad import Controller
from console.core.comms.stm32 import STM32
from console.core.comms.comms import CommunicationManager

PORT = 'COM27'  # ← change if needed

def main():
    # 1. Connect ESP
    print(f"Connecting to ESP on {PORT}...")
    esp = STM32(baudrate=115200)
    esp.connect(PORT)
    time.sleep(2)

    if not esp.connected:
        print("❌ Could not connect to ESP. Check port and try again.")
        return
    print(f"✅ Serial connected")

    # 2. Connect Controller
    controller = Controller()
    time.sleep(0.5)

    if not controller.connected:
        print("⚠️  No controller detected — continuing anyway")
    else:
        print(f"✅ Controller connected: {controller.gamepad}")

    # 3. Start CommunicationManager
    manager = CommunicationManager(esp, controller)
    print("\n🚀 Running! Move sticks to see thruster values change.")
    print("   Press CROSS to toggle LED. Ctrl+C to stop.\n")

    # 4. Print live state
    try:
        while True:
            time.sleep(0.3)
            orientation = manager.orientations_readings
            status      = manager.status
            thrusters   = manager.thrusters_readings
            ctrl        = controller.bindings_state  # ← shows live controller input

            print("─" * 60)

            # Controller inputs
            print(f"  LS: ({ctrl.get('LS-H', 0):+.2f}, {ctrl.get('LS-V', 0):+.2f})  "
                  f"RS: ({ctrl.get('RS-H', 0):+.2f}, {ctrl.get('RS-V', 0):+.2f})  "
                  f"L2: {ctrl.get('L2', 0):.2f}  R2: {ctrl.get('R2', 0):.2f}")

            # Sensor feedback from ESP
            if orientation:
                print(f"  Depth:{orientation['depth']:+.3f}  "
                      f"Yaw:{orientation['yaw']:+.3f}  "
                      f"Pitch:{orientation['pitch']:+.3f}  "
                      f"Roll:{orientation['roll']:+.3f}")
            else:
                print("  Orientation : waiting...")

            if thrusters:
                t_vals = "  ".join(f"t{i+1}:{v:+.2f}" for i, v in enumerate(thrusters.values()))
                print(f"  {t_vals}")
            else:
                print("  Thrusters   : waiting...")

            print(f"  Status: {status}  |  ESP Ready: {esp.esp_ready}")

    except KeyboardInterrupt:
        print("\n🛑 Stopped.")

if __name__ == '__main__':
    main()