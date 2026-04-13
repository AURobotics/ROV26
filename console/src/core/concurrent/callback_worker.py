import inspect
import threading
from typing import Callable
import weakref

def _create_weakref(func: Callable) -> weakref.WeakMethod | weakref.ReferenceType:
    if inspect.ismethod(func) and not inspect.isbuiltin(func):
        return weakref.WeakMethod(func)
    else:
        return weakref.ref(func)

class CallbackWorker:
    def __init__(self, task: Callable, callback: Callable) -> None:
        self._task = task
        self._callback = callback
        self._thread = threading.Thread(target=self._run, daemon=True)

    def run(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        self._task()
        self._callback
