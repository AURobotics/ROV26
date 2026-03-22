import threading
import time

import cv2

from console.assets import get_asset

class Gst:
    EMPTY_FRAME = cv2.imread(get_asset("novideo.png"))
    def __init__(self, pipeline: str) -> None:
        self._cap = cv2.VideoCapture(pipeline)
        self._frame = None
        worker_thread = threading.Thread(target=self._update_frame, daemon=True)
        worker_thread.start()
    
    def _update_frame(self):
        while True:
            time.sleep(0.15)
            _, self._frame = self._cap.read()
    
    @property
    def frame(self):
        return self._frame if self._frame is not None else self.EMPTY_FRAME