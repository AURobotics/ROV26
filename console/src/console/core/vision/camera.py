import cv2
from threading import Thread
from time import sleep
from console.resources import get_resource


class Camera:
    def __init__(self, index) -> None:
        # fallback image if camera fails
        with get_resource("playstation-controller.webp") as empty_frame_image:
            self._empty_frame = cv2.imread(empty_frame_image)
        self._cap = cv2.VideoCapture(index)
        self._cap.open(0)
        self._frame = None
        self._frame_thread = Thread(target=self._frame_loop, daemon=True)
        self._frame_thread.start()

    def _frame_loop(self):
        while True:
            success, image = self._cap.read()
            if success:
                self._frame = image
            else:
                self._cap.release()
                self._cap.open(0)

            sleep(0.015)

    @property
    def frame(self):
        return self._frame if self._frame is not None else self._empty_frame
