import inspect
import threading
from typing import Callable


class CallbackWorker:
    def __init__(
        self, task: Callable, callback: Callable, propagate_exceptions: bool = False
    ) -> None:
        self._task = task
        self._callback = callback
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._propagate_exceptions = propagate_exceptions

    def run(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        try:
            self._task()
        except Exception as ex:
            if not self._propagate_exceptions:
                print(f"[WARN] | {ex}")
            else:
                raise
        finally:
            self._callback()
