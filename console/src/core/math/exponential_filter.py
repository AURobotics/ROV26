import math
import time
from typing import Annotated

from annotated_types import Ge, Gt, Lt


class ExponentialFilter:
    _zero_state_timeout: float | None
    _t_set: float
    _value_prev: float
    _epsilon: float
    _ln_epsilon: float

    def __init__(
        self,
        setting_time: Annotated[float, Gt(0.0)],
        zero_state_timeout: float | None = None,
        setting_percent: Annotated[float, Ge(0.0), Lt(100.0)] = 95.0,
    ) -> None:
        """A exponential smoothing filter

        Args:
            setting_time (float): time in seconds to reach `setting_percent` of the desired value
            zero_state_timeout (float | None): timeout in seconds to consider that the connection has been severed and start the smoothening over; \
            None keeps it manual via :meth:`~ExponentialFilter.set_zero_state()`
            setting_percent (float): the percentage of the desired value at which it is considered settled \
                default: 95%
        """
        self._zero_state_timeout = None
        self.setting_time = setting_time  # validates setting time is not 0
        self._value_prev = 0.0
        self._t_prev = time.perf_counter()
        self.zero_state_timeout = (
            zero_state_timeout  # validates timeout against setting time
        )
        self.setting_percent = setting_percent  # validates percent

    @property
    def setting_percent(self) -> Annotated[float, Ge(0.0), Lt(100.0)]:
        return 100 - 100 * self._epsilon

    @setting_percent.setter
    def setting_percent(self, value: Annotated[float, Ge(0.0), Lt(100.0)]) -> None:
        if not (0.0 <= value <= 100.0):
            raise ValueError("Provided value is not a percentage")
        self._epsilon = (100.0 - value) / 100
        if math.isclose(self._epsilon, 0):
            raise ValueError("Provided setting percentage is too close to 100%")
        self._ln_epsilon = math.log(self._epsilon)

    def set_zero_state(self) -> None:
        self._value_prev = 0.0

    @property
    def zero_state_timeout(self) -> float | None:
        return self._zero_state_timeout

    @zero_state_timeout.setter
    def zero_state_timeout(self, timeout: float | None) -> None:
        if timeout is not None and timeout <= self.setting_time:
            raise ValueError(
                "Zero-state timeout cannot be close to or less than the setting time"
            )
        self._zero_state_timeout = timeout

    @property
    def setting_time(self) -> float:
        return self._t_set

    @setting_time.setter
    def setting_time(self, seconds: Annotated[float, Gt(0.0)]) -> None:
        if math.isclose(seconds, 0.0) or seconds <= 0:
            raise ValueError("Setting time cannot be 0 or negative")
        if self.zero_state_timeout and seconds >= self.zero_state_timeout:
            raise ValueError(
                "Setting time cannot be close to or more than the zero-state timeout"
            )
        self._t_set = seconds

    def filter_step(self, value_raw: float) -> float:
        t = time.perf_counter()
        dt = t - self._t_prev

        if self.zero_state_timeout and dt >= self.zero_state_timeout:
            self.set_zero_state()

        if math.isclose(dt, 0.0):
            return self._value_prev

        self._t_prev = t

        dt = min(dt, self.setting_time)

        alpha = 1 - math.exp(self._ln_epsilon * dt / self.setting_time)

        value_filtered = (alpha * value_raw) + (1 - alpha) * self._value_prev
        self._value_prev = value_filtered
        return value_filtered
