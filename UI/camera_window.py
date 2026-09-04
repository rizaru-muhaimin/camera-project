from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from UIServices import CameraDescriptor, CameraService, list_connected_cameras


class CameraWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Camera Capture")
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "camera.svg"
        self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1100, 720)
        self.settings = QSettings("CameraProject", "CameraCapture")
        self.camera = CameraService()
        self.current_frame: QImage | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.camera_select = QComboBox()
        self.refresh_button = QPushButton("Refresh")
        self.open_button = QPushButton("Open camera")
        self.close_button = QPushButton("Stop camera")
        self.folder_edit = QLineEdit()
        self.folder_button = QPushButton("Browse")
        self.prefix_edit = QLineEdit("photo")
        self.format_select = QComboBox()
        self.format_select.addItems(["jpg", "png"])
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(95)
        self.quality_value = QLabel("95")
        self.capture_button = QPushButton("Capture photo")
        self.preview = QLabel("No camera connected")
        self.status = QLabel("Ready")

        self.build_ui()
        self.load_settings()
        self.refresh_cameras()
        self.refresh_button.clicked.connect(self.refresh_cameras)
        self.open_button.clicked.connect(self.open_camera)
        self.close_button.clicked.connect(self.close_camera)
        self.folder_button.clicked.connect(self.choose_folder)
        self.capture_button.clicked.connect(self.capture_photo)
        self.quality_slider.valueChanged.connect(
            lambda value: self.quality_value.setText(str(value))
        )

    def build_ui(self) -> None:
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(0, 0)
        self.preview.setStyleSheet("background: #20252b; color: #c8d0d9;")
        self.preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        camera_box = QGroupBox("Camera")
        camera_layout = QVBoxLayout(camera_box)
        camera_layout.addWidget(self.camera_select)
        camera_buttons = QHBoxLayout()
        camera_buttons.addWidget(self.refresh_button)
        camera_buttons.addWidget(self.open_button)
        camera_buttons.addWidget(self.close_button)
        camera_layout.addLayout(camera_buttons)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(self.folder_button)
        quality_row = QHBoxLayout()
        quality_row.addWidget(self.quality_slider, 1)
        quality_row.addWidget(self.quality_value)

        save_box = QGroupBox("Save settings")
        save_form = QFormLayout(save_box)
        save_form.addRow("Folder", folder_row)
        save_form.addRow("File prefix", self.prefix_edit)
        save_form.addRow("Format", self.format_select)
        save_form.addRow("JPEG quality", quality_row)
        save_form.addRow(self.capture_button)

        side = QVBoxLayout()
        side.addWidget(camera_box)
        side.addWidget(save_box)
        side.addStretch()
        side.addWidget(self.status)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addLayout(side, 3)
        layout.addWidget(self.preview, 7)
        self.setCentralWidget(central)

    def load_settings(self) -> None:
        self.folder_edit.setText(
            self.settings.value("folder", str(Path.home() / "Pictures"))
        )
        self.prefix_edit.setText(self.settings.value("prefix", "photo"))
        self.format_select.setCurrentText(self.settings.value("format", "jpg"))
        quality = int(self.settings.value("quality", 95))
        quality = max(self.quality_slider.minimum(), min(quality, self.quality_slider.maximum()))
        self.quality_slider.setValue(quality)
        self.quality_value.setText(str(quality))

    def save_settings(self) -> None:
        self.settings.setValue("folder", self.folder_edit.text())
        self.settings.setValue("prefix", self.prefix_edit.text())
        self.settings.setValue("format", self.format_select.currentText())
        self.settings.setValue("quality", self.quality_slider.value())

    def refresh_cameras(self) -> None:
        selected = self.camera_select.currentData()
        self.camera_select.clear()
        for camera in list_connected_cameras():
            self.camera_select.addItem(camera.display_name, camera)
        if selected is not None:
            for position in range(self.camera_select.count()):
                if self.camera_select.itemData(position) == selected:
                    self.camera_select.setCurrentIndex(position)
                    break
        self.status.setText(f"Found {self.camera_select.count()} camera(s)")

    def open_camera(self) -> None:
        camera = self.camera_select.currentData()
        if not isinstance(camera, CameraDescriptor):
            self.status.setText("No camera selected")
            return
        if self.camera.open(camera):
            self.timer.start(33)
            self.status.setText(f"{camera.display_name} connected")
        else:
            detail = self.camera.last_error or "camera access failed"
            self.status.setText(f"Could not open {camera.display_name}: {detail}")

    def close_camera(self) -> None:
        self.timer.stop()
        self.camera.close()
        self.current_frame = None
        self.preview.clear()
        self.preview.setText("No camera connected")
        self.status.setText("Camera stopped")

    def update_frame(self) -> None:
        frame = self.camera.read()
        if frame is None:
            self.status.setText(self.camera.last_error or "No frame received")
            return
        height, width = frame.shape[:2]
        if frame.ndim == 2:
            image = QImage(frame.data, width, height, width, QImage.Format_Grayscale8)
        elif frame.ndim == 3 and frame.shape[2] == 3:
            channels = 3
            image = QImage(
                frame.data, width, height, channels * width, QImage.Format_BGR888
            )
        else:
            self.status.setText(f"Unsupported camera frame shape: {frame.shape}")
            return
        image = image.copy()
        self.current_frame = image
        self.preview.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose save folder")
        if folder:
            self.folder_edit.setText(folder)

    def capture_photo(self) -> None:
        if self.current_frame is None:
            self.status.setText("Open a camera before capturing")
            return
        self.save_settings()
        folder = Path(self.folder_edit.text()).expanduser()
        try:
            path = self.camera.save_frame(
                folder=folder,
                prefix=self.prefix_edit.text().strip() or "photo",
                extension=self.format_select.currentText(),
                quality=self.quality_slider.value(),
            )
        except OSError as error:
            QMessageBox.critical(self, "Save error", str(error))
            return
        self.status.setText(f"Saved: {path}")

    def closeEvent(self, event) -> None:
        self.save_settings()
        self.close_camera()
        event.accept()
