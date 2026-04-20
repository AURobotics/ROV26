import time


class Pwm:
    def __init__(self, duty_cycle: float, period: float) -> None:
        self.duty_cycle = duty_cycle
        self.period = period
        self.last_change = time.perf_counter()
        self.high = False

    def filter(self, high: bool) -> bool:
        if not high:
            return False

        curr_time = time.perf_counter()
        if self.high and curr_time - self.last_change >= self.duty_cycle * self.period:
            self.high = False
            self.last_change = curr_time
        elif not self.high and curr_time - self.last_change >= (1 - self.duty_cycle) * self.period:
            self.high = True
            self.last_change = curr_time
        return self.high
