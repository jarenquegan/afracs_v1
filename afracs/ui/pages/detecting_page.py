"""DETECTING state widget: camera preview."""

import cv2
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

IDLE_TIMEOUT_MS = 15_000


class _CameraView(QWidget):
    """Camera display that uses paintEvent + update() instead of QLabel.setPixmap().

    QLabel.setPixmap() calls updateGeometry() every frame, which pokes the layout
    system and causes continuous resize thrash. update() only schedules a repaint —
    the layout is never touched.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraView")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pixmap: QPixmap | None = None
        self._text = "Initializing camera…"

    def show_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        img = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()
        self._pixmap = QPixmap.fromImage(img)
        self._text = ""
        self.update()

    def show_text(self, text: str) -> None:
        self._pixmap = None
        self._text = text
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        elif self._text:
            painter.setPen(QColor("#D4B356"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text)

    def sizeHint(self) -> QSize:
        return QSize(0, 0)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)


class DetectingPage(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("detectingPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.camera_view = _CameraView()
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
        self.camera_view.show_frame(frame)

    def show_unavailable(self) -> None:
        self.camera_view.show_text("Camera unavailable")

    def mousePressEvent(self, event) -> None:
        self.cancel_requested.emit()
        super().mousePressEvent(event)
