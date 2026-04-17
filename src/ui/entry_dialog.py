"""手动录入对话框 - 精灵/技能录入"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QWidget, QLineEdit, QComboBox, QSpinBox, QTextEdit,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtWidgets import QCompleter

from sqlalchemy.orm import Session

from src.database.models import Attribute, Skill
from src.database.queries import (
    get_all_attributes,
    get_all_skills,
    get_all_sprites,
    add_sprite,
    add_skill,
    add_sprite_skills,
    get_sprite_skill_ids,
)
from src.ui.widgets.pinyin_completer import PinyinCompleter


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
        tabs.addTab(self._build_bind_tab(), "精灵-技能绑定")
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

    # ---- 精灵-技能绑定 ----
    def _build_bind_tab(self) -> QWidget:
        """构建精灵-技能绑定标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 精灵搜索选择器
        sprite_layout = QVBoxLayout()
        sprite_layout.setSpacing(4)

        sprite_label = QLabel("精灵名称：")
        sprite_layout.addWidget(sprite_label)

        self._bind_sprite_search = QLineEdit()
        self._bind_sprite_search.setPlaceholderText("输入精灵名称搜索...")
        self._bind_sprite_search.setClearButtonEnabled(True)
        sprite_layout.addWidget(self._bind_sprite_search)

        # 自动补全
        self._bind_sprite_completer = PinyinCompleter()
        self._bind_sprite_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._bind_sprite_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._bind_sprite_search.setCompleter(self._bind_sprite_completer)

        # 当前选中状态
        self._selected_sprite_label = QLabel("当前未选择精灵")
        self._selected_sprite_label.setStyleSheet("color: #a6adc8; font-style: italic;")
        sprite_layout.addWidget(self._selected_sprite_label)

        layout.addLayout(sprite_layout)

        # 存储精灵数据
        sprites = get_all_sprites(self._session)
        self._sprite_name_to_id = {sp.name: sp.id for sp in sprites}
        sprite_names = list(self._sprite_name_to_id.keys())
        self._bind_sprite_completer.setSourceModel(QStringListModel(sprite_names))

        # 连接补全选中信号
        self._bind_sprite_completer.activated.connect(self._on_sprite_selected)

        # 技能搜索框
        skill_search_layout = QVBoxLayout()
        skill_search_layout.setSpacing(4)

        skill_search_label = QLabel("技能搜索：")
        skill_search_layout.addWidget(skill_search_label)

        self._bind_skill_search = QLineEdit()
        self._bind_skill_search.setPlaceholderText("输入技能名称过滤...")
        self._bind_skill_search.setClearButtonEnabled(True)
        self._bind_skill_search.textChanged.connect(self._filter_skill_list)
        skill_search_layout.addWidget(self._bind_skill_search)

        layout.addLayout(skill_search_layout)

        # 可选技能列表
        skill_label = QLabel("可选技能（可多选）：")
        layout.addWidget(skill_label)

        self._bind_skill_list = QListWidget()
        self._bind_skill_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._bind_skill_list.setMaximumHeight(200)
        skills = get_all_skills(self._session)
        for s in skills:
            item = QListWidgetItem(f"{s.name} ({s.attribute.name})")
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self._bind_skill_list.addItem(item)
        layout.addWidget(self._bind_skill_list)

        # 绑定按钮
        bind_btn = QPushButton("绑定选中技能")
        bind_btn.clicked.connect(self._bind_skills)
        layout.addWidget(bind_btn)

        layout.addStretch()
        return widget

    def _on_sprite_selected(self, sprite_name: str):
        """精灵补全选中时处理"""
        sprite_id = self._sprite_name_to_id.get(sprite_name)
        if sprite_id is None:
            self._selected_sprite_label.setText("当前未选择精灵")
            self._selected_sprite_label.setStyleSheet("color: #a6adc8; font-style: italic;")
            self._bind_skill_list.clearSelection()
            return

        # 更新选中状态显示
        self._selected_sprite_label.setText(f"当前选中：{sprite_name}")
        self._selected_sprite_label.setStyleSheet("color: #89b4fa; font-weight: bold;")

        # 获取该精灵已有技能ID
        existing_skill_ids = get_sprite_skill_ids(self._session, sprite_id)

        # 重排序技能列表（已绑定技能移到顶部）并设置选中状态
        self._reorder_skill_list(existing_skill_ids)

    def _reorder_skill_list(self, existing_skill_ids: list[int]):
        """重排序技能列表，将已绑定技能移到顶部并选中"""
        existing_set = set(existing_skill_ids)

        # 收集所有项目（使用 takeItem 移除）
        all_items = []
        while self._bind_skill_list.count() > 0:
            all_items.append(self._bind_skill_list.takeItem(0))

        # 分离已绑定和未绑定项目
        bound_items = []
        unbound_items = []
        for item in all_items:
            skill_id = item.data(Qt.ItemDataRole.UserRole)
            if skill_id in existing_set:
                bound_items.append(item)
            else:
                unbound_items.append(item)

        # 先添加已绑定技能并选中
        for item in bound_items:
            self._bind_skill_list.addItem(item)
            item.setSelected(True)

        # 再添加未绑定技能
        for item in unbound_items:
            self._bind_skill_list.addItem(item)

        # 滚动到顶部
        self._bind_skill_list.scrollToTop()

    def _filter_skill_list(self, text: str):
        """过滤技能列表（支持拼音首字母）"""
        from src.utils.pinyin_service import PinyinService

        search_text = text.strip()
        for i in range(self._bind_skill_list.count()):
            item = self._bind_skill_list.item(i)
            if not search_text:
                item.setHidden(False)
            else:
                # 提取技能名称（格式: "技能名 (属性)"）
                item_text = item.text()
                skill_name = item_text.split(' (')[0]
                item.setHidden(not PinyinService.match(skill_name, search_text))

    def _bind_skills(self):
        """绑定选中的技能到当前精灵"""
        sprite_name = self._bind_sprite_search.text().strip()
        if not sprite_name:
            QMessageBox.warning(self, "提示", "请先搜索并选择精灵")
            return

        sprite_id = self._sprite_name_to_id.get(sprite_name)
        if sprite_id is None:
            QMessageBox.warning(self, "提示", "未找到该精灵，请从补全列表中选择")
            return

        skill_ids = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._bind_skill_list.selectedItems()
        ]

        if not skill_ids:
            QMessageBox.warning(self, "提示", "请至少选择一个技能")
            return

        try:
            count = add_sprite_skills(self._session, sprite_id, skill_ids)
            if count == 0:
                QMessageBox.information(self, "提示", "选中的技能已全部绑定")
            else:
                QMessageBox.information(self, "成功", f"已为「{sprite_name}」绑定 {count} 个技能")
        except ValueError as e:
            QMessageBox.warning(self, "警告", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"绑定失败：{e}")
