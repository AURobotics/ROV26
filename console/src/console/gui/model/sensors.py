from console.comms.comms import CommunicationManager


class Sensors:
    def __init__(self, comms_manager: CommunicationManager):
        self._comms = comms_manager

    def thruster(self, num: int) -> float:
        return self._comms.sensor_cache.thrusters[num - 1]

    @property
    def yaw(self) -> float:
        return self._comms.sensor_cache.yaw

    @property
    def pitch(self) -> float:
        return self._comms.sensor_cache.pitch

    @property
    def roll(self) -> float:
        return self._comms.sensor_cache.roll