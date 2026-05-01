"""DETECTING state widget: camera preview."""

import cv2
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

IDLE_TIMEOUT_MS = 15_000


class DetectingPage(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("detectingPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.camera_view = QLabel("Initializing camera…")
        self.camera_view.setObjectName("cameraView")
        self.camera_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_view.setScaledContents(False)
        layout.addWidget(self.camera_view, stretch=1)

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self.cancel_requested)

    def enter(self, **_ctx) -> None:
        self._idle_timer.start(IDLE_TIMEOUT_MS)

    def leave(self) -> None:
        self._idle_timer.stop()

    def face_detected(self) -> None:
        self._idle_timer.start(IDLE_TIMEOUT_MS)

    def show_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        img = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(img).scaled(
            self.camera_view.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.camera_view.setPixmap(pix)

    def show_unavailable(self) -> None:
        self.camera_view.setText("Camera unavailable")

    def mousePressEvent(self, event) -> None:
        self.cancel_requested.emit()
        super().mousePressEvent(event)
