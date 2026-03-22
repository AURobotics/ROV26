import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer
import cv2


def bootstrap_gstreamer():
    """Sets up the local ROV26 GStreamer environment."""
    base_dir = Path(__file__).resolve().parent
    bin_dir = base_dir / "bin" / "linux_x64"

    os.environ["LD_LIBRARY_PATH"] = f"{bin_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ["GST_PLUGIN_PATH"] = str(bin_dir / "gstreamer-1.0")
    os.environ["GST_PLUGIN_SCANNER"] = str(bin_dir / "helpers" / "gst-plugin-scanner")
    os.environ["GST_REGISTRY"] = str(bin_dir / "registry.bin")


# Initialize before PySide/OpenCV imports logic
bootstrap_gstreamer()


class ROVConsole(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROV26 Console - PySide6")
        self.resize(800, 600)

        # UI Setup
        self.video_label = QLabel("Waiting for Stream...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # GStreamer Pipeline
        self.pipeline = (
            "udpsrc address=239.1.1.1 port=5000 auto-multicast=true ! "
            "application/x-rtp, payload=96 ! "
            "rtph264depay ! h264parse ! avdec_h264 ! "
            "videoconvert ! appsink drop=true sync=false"
        )
        self.cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)

        # Timer to refresh frames (approx 30fps)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(15)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert OpenCV BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w

            # Convert to QImage and show
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.video_label.setPixmap(
                QPixmap.fromImage(q_img).scaled(
                    self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def closeEvent(self, event):
        self.cap.release()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ROVConsole()
    window.show()
    sys.exit(app.exec())
