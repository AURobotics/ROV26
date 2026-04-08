# opencv-build

Wheel builds for `opencv-python` with GStreamer support, designed to work with `gstreamer-bundle` or any of its sub-packages with a hard dependency on `gstreamer-libs` specifically.

Due to the difficulty faced here and on GStreamer's team's front in making distribution-agnostic wheels with GStreamer support for Linux, Linux wheels have been dropped. For now, Linux users should use their distribution's `opencv-python` and `gstreamer` packages if available.

Current supported platforms:
- Windows and all supported CPU architectures

Supportable platforms:
- MacOS (needs build trials on a compatible machine or remote pipeline)

Unsupported platforms:
- Other desktop Linux/ Unix (waiting to see GStreamer's approach to wheels on them)
- Mobile


Adding support for different platforms requires adding the platform-specific `gstreamer-libs` loader hook to the `cv2/__init__.py` file and optionally platform-specific `pyinstaller` hooks in [patch_opencv.py](./patch_opencv.py)