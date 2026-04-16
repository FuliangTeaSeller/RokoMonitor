"""悬浮窗 - 置顶显示对方精灵信息"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QIcon

from src.database.queries import SpriteInfo, SkillInfo
from src.ui.image_utils import load_icon


class OverlayWindow(QWidget):
    """置顶悬浮窗，展示精灵属性与技能池"""

    def __init__(self, sprite_info: SpriteInfo, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()
        self._sprite_info = sprite_info
        self._init_ui()
        self._load_data(sprite_info)

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(380, 420)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
            }
            QPushButton {
                background: transparent;
                color: #f38ba8;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #eba0ac;
            }
            QTableWidget {
                background-color: #181825;
                gridline-color: #313244;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 2px 4px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                padding: 4px;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)

        # 标题栏（可拖动）
        title_bar = QHBoxLayout()

        # 精灵图标
        self._sprite_icon_label = QLabel()
        self._sprite_icon_label.setFixedSize(40, 40)
        self._sprite_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_bar.addWidget(self._sprite_icon_label)

        self._name_label = QLabel()
        self._name_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title_bar.addWidget(self._name_label)
        title_bar.addStretch()

        self._attr_label = QLabel()
        self._attr_label.setFont(QFont("Microsoft YaHei", 10))
        title_bar.addWidget(self._attr_label)
        title_bar.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #45475a;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 技能表格
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["", "技能", "属性", "类别", "威力", "能耗"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        # 列宽
        self._table.setColumnWidth(0, 32)  # 图标列
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(2, 45)
        self._table.setColumnWidth(3, 45)
        self._table.setColumnWidth(4, 45)
        self._table.setColumnWidth(5, 45)
        layout.addWidget(self._table)

        # 描述区
        self._desc_label = QLabel("点击技能查看描述")
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("color: #a6adc8; font-size: 11px; padding: 4px;")
        layout.addWidget(self._desc_label)

        self._table.cellClicked.connect(self._on_skill_clicked)

    def _load_data(self, info: SpriteInfo):
        self._sprite_info = info
        self._name_label.setText(info.name)
        self._attr_label.setText(" / ".join(info.attributes))

        # 加载并显示精灵图标
        sprite_icon = load_icon(info.image_path, size=(36, 36))
        if sprite_icon:
            self._sprite_icon_label.setPixmap(sprite_icon)
        else:
            self._sprite_icon_label.clear()

        self._table.setRowCount(len(info.skills))
        for row, skill in enumerate(info.skills):
            # 技能图标列
            icon = load_icon(skill.image_path, size=(24, 24))
            if icon:
                icon_item = QTableWidgetItem()
                icon_item.setIcon(QIcon(icon))
                self._table.setItem(row, 0, icon_item)
            else:
                self._table.setItem(row, 0, QTableWidgetItem(""))

            self._table.setItem(row, 1, QTableWidgetItem(skill.name))
            self._table.setItem(row, 2, QTableWidgetItem(skill.attribute))
            self._table.setItem(row, 3, QTableWidgetItem(skill.category))
            power_text = str(skill.power) if skill.power else "—"
            self._table.setItem(row, 4, QTableWidgetItem(power_text))
            self._table.setItem(row, 5, QTableWidgetItem(str(skill.energy_consumption)))

    def _on_skill_clicked(self, row, _col):
        if 0 <= row < len(self._sprite_info.skills):
            skill = self._sprite_info.skills[row]
            desc = skill.description or "无描述"
            self._desc_label.setText(f"{skill.name}：{desc}")

    # --- 拖动支持 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()
