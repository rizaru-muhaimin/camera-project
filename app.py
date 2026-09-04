from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from UI import CameraWindow


def main() -> int:
    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "assets" / "camera.svg"
    app.setWindowIcon(QIcon(str(icon_path)))
    window = CameraWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())