import time


class Pwm:
    def __init__(self, duty_cycle: float) -> None:
        self.duty_cycle = duty_cycle
        self.last_change = time.perf_counter()
        self.high = False

    def filter(self, high: bool) -> bool:
        if not high:
            return False

        curr_time = time.perf_counter()

        if curr_time - self.last_change >= self.duty_cycle:
            self.high = not self.high
            self.last_change = curr_time
        return self.high
