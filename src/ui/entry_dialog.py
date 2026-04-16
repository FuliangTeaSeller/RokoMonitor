"""手动录入对话框 - 精灵/技能录入"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QWidget, QLineEdit, QComboBox, QSpinBox, QTextEdit,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt

from sqlalchemy.orm import Session

from src.database.models import Attribute, Skill
from src.database.queries import get_all_attributes, get_all_skills, get_all_sprites, add_sprite, add_skill


class EntryDialog(QDialog):
    """手动录入对话框，含精灵录入与技能录入两个标签页"""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self._session = session
        self.setWindowTitle("手动录入")
        self.setMinimumSize(450, 500)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_sprite_tab(), "精灵录入")
        tabs.addTab(self._build_skill_tab(), "技能录入")
        layout.addWidget(tabs)

    # ---- 精灵录入 ----
    def _build_sprite_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self._sp_name = QLineEdit()
        layout.addRow("精灵名称：", self._sp_name)

        # 属性多选
        self._sp_attr_list = QListWidget()
        self._sp_attr_list.setMaximumHeight(120)
        attrs = get_all_attributes(self._session)
        for a in attrs:
            item = QListWidgetItem(a.name)
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            self._sp_attr_list.addItem(item)
        layout.addRow("属性（可多选）：", self._sp_attr_list)

        # 技能多选
        self._sp_skill_list = QListWidget()
        self._sp_skill_list.setMaximumHeight(180)
        skills = get_all_skills(self._session)
        for s in skills:
            item = QListWidgetItem(f"{s.name} ({s.attribute.name})")
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self._sp_skill_list.addItem(item)
        layout.addRow("可选技能（可多选）：", self._sp_skill_list)

        save_btn = QPushButton("保存精灵")
        save_btn.clicked.connect(self._save_sprite)
        layout.addRow(save_btn)

        return widget

    def _save_sprite(self):
        name = self._sp_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入精灵名称")
            return

        attr_ids = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._sp_attr_list.selectedItems()
        ]
        skill_ids = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._sp_skill_list.selectedItems()
        ]

        if not attr_ids:
            QMessageBox.warning(self, "提示", "请至少选择一个属性")
            return

        try:
            add_sprite(self._session, name, attr_ids, skill_ids)
            QMessageBox.information(self, "成功", f"精灵「{name}」已添加")
            self._sp_name.clear()
            self._sp_attr_list.clearSelection()
            self._sp_skill_list.clearSelection()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败：{e}")

    # ---- 技能录入 ----
    def _build_skill_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        self._sk_name = QLineEdit()
        layout.addRow("技能名称：", self._sk_name)

        self._sk_attr = QComboBox()
        attrs = get_all_attributes(self._session)
        for a in attrs:
            self._sk_attr.addItem(a.name, a.id)
        layout.addRow("技能属性：", self._sk_attr)

        self._sk_category = QComboBox()
        self._sk_category.addItems(["物攻", "魔攻", "变化"])
        layout.addRow("类别：", self._sk_category)

        self._sk_power = QSpinBox()
        self._sk_power.setRange(0, 999)
        self._sk_power.setSpecialValueText("—（变化类）")
        layout.addRow("威力：", self._sk_power)

        self._sk_energy = QSpinBox()
        self._sk_energy.setRange(1, 20)
        self._sk_energy.setValue(3)
        layout.addRow("能量消耗：", self._sk_energy)

        self._sk_desc = QTextEdit()
        self._sk_desc.setMaximumHeight(80)
        layout.addRow("描述：", self._sk_desc)

        save_btn = QPushButton("保存技能")
        save_btn.clicked.connect(self._save_skill)
        layout.addRow(save_btn)

        return widget

    def _save_skill(self):
        name = self._sk_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入技能名称")
            return

        category = self._sk_category.currentText()
        power = self._sk_power.value() if category != "变化" else None
        description = self._sk_desc.toPlainText().strip() or None

        try:
            add_skill(
                self._session,
                name=name,
                attribute_id=self._sk_attr.currentData(),
                category=category,
                energy_consumption=self._sk_energy.value(),
                power=power,
                description=description,
            )
            QMessageBox.information(self, "成功", f"技能「{name}」已添加")
            self._sk_name.clear()
            self._sk_desc.clear()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败：{e}")
