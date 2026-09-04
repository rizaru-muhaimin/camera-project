from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


root = Path(__file__).resolve().parent.parent
svg_path = root / "assets" / "camera.svg"
ico_path = root / "assets" / "camera.ico"
renderer = QSvgRenderer(str(svg_path))
if not renderer.isValid():
    raise RuntimeError(f"Invalid SVG asset: {svg_path}")

image = QImage(QSize(256, 256), QImage.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
renderer.render(painter)
painter.end()
if not image.save(str(ico_path), "ICO"):
    raise RuntimeError(f"Could not create icon: {ico_path}")
print(ico_path)
