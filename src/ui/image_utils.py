"""图片加载辅助工具类"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtWidgets import QWidget

from src.config import PROJECT_ROOT


def load_icon(image_path: str | None, size: tuple[int, int] = (32, 32)) -> Optional[QPixmap]:
    """
    加载图片为图标

    Args:
        image_path: 图片相对路径，如 "data/images/skills/1.png"
        size: 目标尺寸 (width, height)

    Returns:
        QPixmap 对象，如果图片不存在或加载失败返回 None
    """
    if not image_path:
        return None

    full_path = PROJECT_ROOT / image_path
    if not full_path.exists():
        return None

    pixmap = QPixmap(str(full_path))
    if pixmap.isNull():
        return None

    return pixmap.scaled(*size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


class IconWidget(QWidget):
    """带图标的标签组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon = None

    def set_icon(self, pixmap: QPixmap | None):
        """设置图标并重绘"""
        self._icon = pixmap
        self.update()

    def paintEvent(self, event):
        """绘制图标"""
        if self._icon:
            painter = QPainter(self)
            # 居中绘制
            x = (self.width() - self._icon.width()) // 2
            y = (self.height() - self._icon.height()) // 2
            painter.drawPixmap(x, y, self._icon)
