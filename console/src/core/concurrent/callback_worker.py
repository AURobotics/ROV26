import inspect
import threading
from typing import Callable


class CallbackWorker:
    def __init__(self, task: Callable, callback: Callable) -> None:
        self._task = task
        self._callback = callback
        self._thread = threading.Thread(target=self._run, daemon=True)

    def run(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        try:
            self._task()
        except Exception as ex:
            print(f"[WARN] | {ex}")
        finally:
            self._callback()
