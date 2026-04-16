"""主窗口 - 搜索精灵、展示技能池、打开悬浮窗/录入"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFrame,
    QListWidget, QListWidgetItem, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from sqlalchemy.orm import Session

from src.database.queries import search_sprites_by_name, get_sprite_detail, SpriteInfo, SkillInfo
from src.ui.overlay import OverlayWindow
from src.ui.entry_dialog import EntryDialog
from src.ui.image_utils import load_icon


class MainWindow(QMainWindow):
    def __init__(self, session: Session):
        super().__init__()
        self._session = session
        self._overlays: list[OverlayWindow] = []
        self._current_sprite: SpriteInfo | None = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("RokoMonitor - 洛克王国对战辅助")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #cdd6f4;
                background: transparent;
            }
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #313244;
            }
            QTableWidget {
                background-color: #181825;
                gridline-color: #313244;
                border: 1px solid #313244;
                border-radius: 4px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
            QTableWidget::item:selected {
                background-color: #45475a;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                padding: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                font-size: 13px;
            }
            QListWidget::item:selected {
                background-color: #45475a;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # --- 搜索栏 ---
        search_layout = QHBoxLayout()
        search_label = QLabel("精灵名称：")
        search_label.setFont(QFont("Microsoft YaHei", 11))
        search_layout.addWidget(search_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("输入精灵名称搜索...")
        self._search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search_input)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(search_btn)

        overlay_btn = QPushButton("悬浮窗查看")
        overlay_btn.clicked.connect(self._show_overlay)
        search_layout.addWidget(overlay_btn)

        entry_btn = QPushButton("手动录入")
        entry_btn.clicked.connect(self._open_entry_dialog)
        search_layout.addWidget(entry_btn)

        layout.addLayout(search_layout)

        # --- 搜索结果列表 ---
        result_label = QLabel("搜索结果")
        result_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(result_label)

        self._result_list = QListWidget()
        self._result_list.setMaximumHeight(120)
        self._result_list.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self._result_list)

        # --- 技能池详情 ---
        detail_label = QLabel("技能池")
        detail_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(detail_label)

        self._sprite_info_label = QLabel("")
        self._sprite_info_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(self._sprite_info_label)

        self._skill_table = QTableWidget()
        self._skill_table.setColumnCount(7)
        self._skill_table.setHorizontalHeaderLabels(["", "技能", "属性", "类别", "威力", "能耗", "描述"])
        self._skill_table.horizontalHeader().setStretchLastSection(True)
        self._skill_table.verticalHeader().setVisible(False)
        self._skill_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._skill_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._skill_table.setAlternatingRowColors(True)
        self._skill_table.setColumnWidth(0, 36)  # 图标列
        self._skill_table.setColumnWidth(1, 90)
        self._skill_table.setColumnWidth(2, 50)
        self._skill_table.setColumnWidth(3, 50)
        self._skill_table.setColumnWidth(4, 50)
        self._skill_table.setColumnWidth(5, 50)
        layout.addWidget(self._skill_table)

    def _do_search(self):
        keyword = self._search_input.text().strip()
        if not keyword:
            return

        results = search_sprites_by_name(self._session, keyword)
        self._result_list.clear()
        for sp in results:
            # 加载精灵图标
            icon = load_icon(sp.image_path, size=(32, 32))
            if icon:
                item = QListWidgetItem(QIcon(icon), f"{sp.name}  [{'/'.join(sp.attributes)}]")
            else:
                item = QListWidgetItem(f"{sp.name}  [{'/'.join(sp.attributes)}]")
            item.setData(Qt.ItemDataRole.UserRole, sp.id)
            self._result_list.addItem(item)

        if not results:
            self._sprite_info_label.setText("未找到匹配的精灵")
            self._skill_table.setRowCount(0)

    def _on_result_clicked(self, item: QListWidgetItem):
        sprite_id = item.data(Qt.ItemDataRole.UserRole)
        info = get_sprite_detail(self._session, sprite_id)
        if info is None:
            return
        self._current_sprite = info
        self._display_sprite(info)

    def _display_sprite(self, info: SpriteInfo):
        self._sprite_info_label.setText(f"{info.name}  [{'/'.join(info.attributes)}]")
        self._skill_table.setRowCount(len(info.skills))
        for row, skill in enumerate(info.skills):
            # 技能图标列
            icon = load_icon(skill.image_path, size=(24, 24))
            if icon:
                icon_item = QTableWidgetItem()
                icon_item.setIcon(QIcon(icon))
                self._skill_table.setItem(row, 0, icon_item)
            else:
                self._skill_table.setItem(row, 0, QTableWidgetItem(""))

            self._skill_table.setItem(row, 1, QTableWidgetItem(skill.name))
            self._skill_table.setItem(row, 2, QTableWidgetItem(skill.attribute))
            self._skill_table.setItem(row, 3, QTableWidgetItem(skill.category))
            power_text = str(skill.power) if skill.power else "—"
            self._skill_table.setItem(row, 4, QTableWidgetItem(power_text))
            self._skill_table.setItem(row, 5, QTableWidgetItem(str(skill.energy_consumption)))
            desc_text = skill.description or ""
            self._skill_table.setItem(row, 6, QTableWidgetItem(desc_text))

    def _show_overlay(self):
        if self._current_sprite is None:
            QMessageBox.information(self, "提示", "请先搜索并选择一只精灵")
            return
        overlay = OverlayWindow(self._current_sprite)
        overlay.show()
        self._overlays.append(overlay)

    def _open_entry_dialog(self):
        dlg = EntryDialog(self._session, self)
        dlg.exec()
