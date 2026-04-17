"""配队识别对话框"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QRadioButton, QButtonGroup, QSpinBox, QScrollArea, QWidget,
    QGridLayout, QMessageBox, QFrame, QFrame as QtFrame, QLineEdit,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage
import numpy as np

from sqlalchemy.orm import Session

from src.database.queries import get_sprite_detail_by_name, get_sprite_detail, search_sprites_by_name, SpriteInfo, SkillInfo
from src.config import CAPTURE_REGIONS, OCR_CONFIG
from src.capture.screen_capture import ScreenCapture
from src.ocr.engine import OCREngine
from src.ocr.text_match import SpriteMatcher
from src.ui.image_utils import load_icon

# 配置日志
logger = logging.getLogger(__name__)


class SpriteSearchDialog(QDialog):
    """精灵搜索对话框（带自动补全）"""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._selected_sprite: Optional[SpriteInfo] = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("选择精灵")
        self.setFixedSize(400, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
                background: transparent;
            }
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 2px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QListWidget::item:hover {
                background-color: #313244;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel("输入精灵名称或拼音首字母")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 搜索输入框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("例如：火花 或 hs")
        self._search_input.textChanged.connect(self._on_search)
        layout.addWidget(self._search_input)

        # 搜索结果列表
        self._result_list = QListWidget()
        self._result_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._result_list)

        # 按钮
        btn_layout = QHBoxLayout()
        self._confirm_btn = QPushButton("确认")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self._confirm_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

        # 列表选择事件
        self._result_list.itemSelectionChanged.connect(self._on_selection_changed)

        # 初始加载所有精灵
        self._load_all_sprites()

    def _load_all_sprites(self):
        """加载所有精灵"""
        results = search_sprites_by_name(self.session, "")
        self._display_results(results)

    def _on_search(self, text: str):
        """搜索输入变化"""
        keyword = text.strip()
        if keyword:
            results = search_sprites_by_name(self.session, keyword)
        else:
            results = search_sprites_by_name(self.session, "")
        self._display_results(results)

    def _display_results(self, sprites: list[SpriteInfo]):
        """显示搜索结果"""
        self._result_list.clear()
        for sprite in sprites:
            item = QListWidgetItem(f"{sprite.name}  ({' / '.join(sprite.attributes) if sprite.attributes else '未知'})")
            item.setData(Qt.ItemDataRole.UserRole, sprite)
            self._result_list.addItem(item)

    def _on_selection_changed(self):
        """列表选择变化"""
        selected = self._result_list.selectedItems()
        self._confirm_btn.setEnabled(len(selected) > 0)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击选择"""
        self.accept()

    def accept(self):
        """确认选择"""
        selected = self._result_list.selectedItems()
        if selected:
            basic_info = selected[0].data(Qt.ItemDataRole.UserRole)
            # 获取完整信息（包含技能）
            self._selected_sprite = get_sprite_detail(self.session, basic_info.id)
        super().accept()

    def get_selected_sprite(self) -> Optional[SpriteInfo]:
        """获取选中的精灵"""
        return self._selected_sprite


class SkillDetailItem(QPushButton):
    """技能详情卡片（右侧技能项）"""

    def __init__(self, skill: SkillInfo, parent=None):
        super().__init__(parent)
        self._skill = skill
        self._init_ui()

    def _init_ui(self):
        skill = self._skill
        self.setFixedSize(320, 80)  # 加宽以容纳三列布局
        self.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                text-align: left;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # 左：技能图标
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(40, 40)
        if skill.image_path:
            icon = load_icon(skill.image_path, size=(40, 40))
            if icon:
                self._icon_label.setPixmap(icon)
        layout.addWidget(self._icon_label)

        # 中：技能名 && 属性、能耗、威力
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(2)

        # 名称
        name_label = QLabel(skill.name)
        name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #cdd6f4; background: transparent;")
        middle_layout.addWidget(name_label)

        # 属性 + 能耗 + 威力
        attr_info = f"[{skill.attribute}]  能耗:{skill.energy_consumption}"
        if skill.power:
            attr_info += f"  威力:{skill.power}"
        elif skill.category == "变化":
            attr_info += "  变化"
        attr_label = QLabel(attr_info)
        attr_label.setFont(QFont("Microsoft YaHei", 9))
        attr_label.setStyleSheet("color: #89b4fa; background: transparent;")
        middle_layout.addWidget(attr_label)

        layout.addLayout(middle_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("background-color: #45475a;")
        layout.addWidget(separator)

        # 右：技能效果详情
        desc_layout = QVBoxLayout()
        if skill.description:
            desc_label = QLabel(skill.description)
            desc_label.setFont(QFont("Microsoft YaHei", 9))
            desc_label.setStyleSheet("color: #a6adc8; background: transparent;")
            desc_label.setWordWrap(True)
            desc_label.setMaximumWidth(150)
            desc_layout.addWidget(desc_label)
        else:
            empty_label = QLabel("无描述")
            empty_label.setFont(QFont("Microsoft YaHei", 9))
            empty_label.setStyleSheet("color: #585b70; background: transparent;")
            desc_layout.addWidget(empty_label)

        layout.addLayout(desc_layout, 1)  # 描述区域可伸展


class SpriteRowWidget(QFrame):
    """精灵-技能行组件（左右一行）"""

    # 信号：行被选中
    clicked = pyqtSignal(int)  # 参数：行索引

    def __init__(self, row_index: int, sprite_info: Optional[SpriteInfo] = None, parent=None):
        super().__init__(parent)
        self._row_index = row_index
        self._sprite_info = sprite_info
        self._selected = False
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-bottom: 1px solid #45475a;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧：精灵信息（头像 + 名字/属性）
        self._left_frame = QFrame()
        self._left_frame.setFixedWidth(180)
        self._left_frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border: none;
            }
        """)
        self._left_frame.mousePressEvent = lambda e: self.clicked.emit(self._row_index)

        left_layout = QHBoxLayout(self._left_frame)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(10)

        # 精灵图标
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(48, 48)
        left_layout.addWidget(self._icon_label)

        # 精灵名称和属性
        name_attr_layout = QVBoxLayout()
        name_attr_layout.setSpacing(2)

        self._name_label = QLabel()
        self._name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self._name_label.setStyleSheet("color: #cdd6f4; background: transparent;")
        name_attr_layout.addWidget(self._name_label)

        self._attr_label = QLabel()
        self._attr_label.setFont(QFont("Microsoft YaHei", 9))
        self._attr_label.setStyleSheet("color: #89b4fa; background: transparent;")
        name_attr_layout.addWidget(self._attr_label)

        left_layout.addLayout(name_attr_layout)
        left_layout.addStretch()
        layout.addWidget(self._left_frame)

        # 右侧：技能列表（横向滚动）
        self._right_scroll = QScrollArea()
        self._right_scroll.setWidgetResizable(True)
        self._right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._right_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #181825;
                border: none;
            }
            QScrollBar:horizontal {
                background-color: #181825;
                height: 8px;
            }
            QScrollBar::handle:horizontal {
                background-color: #45475a;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #585b70;
            }
        """)

        self._skills_container = QWidget()
        self._skills_layout = QHBoxLayout(self._skills_container)
        self._skills_layout.setContentsMargins(10, 10, 10, 10)
        self._skills_layout.setSpacing(10)
        self._skills_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._right_scroll.setWidget(self._skills_container)
        layout.addWidget(self._right_scroll, 1)

        # 初始化显示
        self._update_display()

    def _update_display(self):
        """更新显示内容"""
        # 清空技能布局
        while self._skills_layout.count():
            child = self._skills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if self._sprite_info:
            # 显示精灵信息
            if self._sprite_info.image_path:
                icon = load_icon(self._sprite_info.image_path, size=(48, 48))
                if icon:
                    self._icon_label.setPixmap(icon)
            self._name_label.setText(self._sprite_info.name)
            if self._sprite_info.attributes:
                self._attr_label.setText(" / ".join(self._sprite_info.attributes))
            else:
                self._attr_label.setText("未知")

            # 显示技能
            if self._sprite_info.skills:
                for skill in self._sprite_info.skills:
                    item = SkillDetailItem(skill)
                    item.clicked.connect(lambda checked, s=skill: self._show_skill_detail(s))
                    self._skills_layout.addWidget(item)
            else:
                empty_label = QLabel("暂无技能数据")
                empty_label.setStyleSheet("color: #a6adc8; font-size: 12px; background: transparent;")
                self._skills_layout.addWidget(empty_label)
        else:
            # 空槽位
            self._icon_label.clear()
            self._name_label.setText(f"槽位 {self._row_index + 1}")
            self._name_label.setStyleSheet("color: #a6adc8; background: transparent;")
            self._attr_label.setText("空")
            self._attr_label.setStyleSheet("color: #585b70; background: transparent;")

            empty_label = QLabel("点击左侧选中此槽位")
            empty_label.setStyleSheet("color: #585b70; font-size: 12px; background: transparent;")
            self._skills_layout.addWidget(empty_label)

        self._skills_layout.addStretch()

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self._selected = selected
        if selected:
            self._left_frame.setStyleSheet("""
                QFrame {
                    background-color: #45475a;
                    border: 2px solid #89b4fa;
                    border-radius: 4px;
                }
            """)
        else:
            self._left_frame.setStyleSheet("""
                QFrame {
                    background-color: #313244;
                    border: none;
                }
            """)

    def set_sprite(self, sprite_info: Optional[SpriteInfo]):
        """设置精灵数据"""
        self._sprite_info = sprite_info
        self._update_display()

    def get_sprite(self) -> Optional[SpriteInfo]:
        """获取精灵数据"""
        return self._sprite_info

    def is_empty(self) -> bool:
        """是否为空槽位"""
        return self._sprite_info is None

    def _show_skill_detail(self, skill: SkillInfo):
        """显示技能详情"""
        detail = f"【{skill.name}】\n\n"
        detail += f"属性：{skill.attribute}\n"
        detail += f"类别：{skill.category}\n"
        if skill.power:
            detail += f"威力：{skill.power}\n"
        detail += f"能耗：{skill.energy_consumption}\n"
        if skill.description:
            detail += f"\n效果：\n{skill.description}"

        QMessageBox.information(self, "技能详情", detail)


class TeamRecognitionDialog(QDialog):
    """配队识别对话框"""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._init_ui()
        self._init_components()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("配队识别 - RokoMonitor")
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)  # 默认较大尺寸

        # 支持最大化
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
                background: transparent;
            }
            QRadioButton {
                color: #cdd6f4;
            }
            QSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px;
            }
            QScrollArea {
                border: 1px solid #313244;
                border-radius: 6px;
                background-color: #181825;
            }
        """)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 识别控制区、状态信息区、截图预览区放在一行
        self._top_layout = QHBoxLayout()
        self._control_group = self._create_control_group()
        self._status_group = self._create_status_group()
        self._screenshot_group = self._create_screenshot_group()
        self._top_layout.addWidget(self._control_group, 1)  # 控制区可伸展
        self._top_layout.addWidget(self._status_group, 0)   # 状态区固定宽度
        self._top_layout.addWidget(self._screenshot_group, 0)  # 截图区固定宽度
        layout.addLayout(self._top_layout)

        # 识别结果区
        self._results_group = self._create_results_group()
        layout.addWidget(self._results_group, 1)  # expand=1

    def _create_control_group(self) -> QFrame:
        """创建识别控制区"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        # 标题
        title = QLabel("识别控制")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 识别模式
        mode_layout = QHBoxLayout()
        mode_label = QLabel("识别模式：")
        self._single_mode_radio = QRadioButton("单次识别")
        self._auto_mode_radio = QRadioButton("自动识别")
        self._single_mode_radio.setChecked(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._single_mode_radio)
        self._mode_group.addButton(self._auto_mode_radio)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self._single_mode_radio)
        mode_layout.addWidget(self._auto_mode_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 间隔设置（仅在自动模式下显示）
        interval_layout = QHBoxLayout()
        interval_label = QLabel("识别间隔（秒）：")
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 10)
        self._interval_spin.setValue(OCR_CONFIG["auto_interval"] // 1000)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self._interval_spin)
        interval_layout.addStretch()
        interval_layout.addSpacing(120)
        layout.addLayout(interval_layout)

        # 截图区域
        region_layout = QHBoxLayout()
        region_label = QLabel("截图区域：")
        self._top_right_radio = QRadioButton("右上角（单精灵）")
        self._team_list_radio = QRadioButton("配队列表（全阵容）")
        self._top_right_radio.setChecked(True)
        self._region_group = QButtonGroup(self)
        self._region_group.addButton(self._top_right_radio)
        self._region_group.addButton(self._team_list_radio)
        region_layout.addWidget(region_label)
        region_layout.addWidget(self._top_right_radio)
        region_layout.addWidget(self._team_list_radio)
        region_layout.addStretch()
        layout.addLayout(region_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        self._start_btn = QPushButton("开始识别")
        self._stop_btn = QPushButton("停止")
        self._stop_btn.setEnabled(False)
        self._cover_recognize_btn = QPushButton("识别覆盖")
        self._cover_recognize_btn.setEnabled(False)
        self._cover_manual_btn = QPushButton("手动输入")
        self._cover_manual_btn.setEnabled(False)
        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._stop_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self._cover_recognize_btn)
        btn_layout.addWidget(self._cover_manual_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return frame

    def _create_screenshot_group(self) -> QtFrame:
        """创建截图显示区"""
        frame = QtFrame()
        frame.setFixedWidth(280)  # 固定宽度
        frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        # 标题
        title = QLabel("截图预览")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 截图显示标签
        self._screenshot_label = QLabel()
        self._screenshot_label.setMinimumSize(250, 150)
        self._screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._screenshot_label.setStyleSheet("""
            QLabel {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
            }
        """)
        self._screenshot_label.setText("等待截图...")
        layout.addWidget(self._screenshot_label)

        return frame

    def _create_results_group(self) -> QFrame:
        """创建识别结果区"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        # 标题栏（标题 + 全屏按钮）
        title_layout = QHBoxLayout()
        title = QLabel("识别结果")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()

        self._fullscreen_btn = QPushButton("全屏展示")
        self._fullscreen_btn.setCheckable(True)
        self._fullscreen_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #585b70;
                border-color: #89b4fa;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen_results)
        title_layout.addWidget(self._fullscreen_btn)

        layout.addLayout(title_layout)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setSpacing(12)
        self._results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._results_container)

        layout.addWidget(scroll)

        return frame

    def _create_status_group(self) -> QFrame:
        """创建状态信息区"""
        frame = QFrame()
        frame.setFixedWidth(150)  # 固定宽度
        frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        self._status_label = QLabel("状态：就绪")
        self._count_label = QLabel("识别次数：0")
        self._success_label = QLabel("成功率：0%")

        layout.addWidget(self._status_label)
        layout.addWidget(self._count_label)
        layout.addWidget(self._success_label)
        layout.addStretch()

        return frame

    def _init_components(self):
        """初始化组件"""
        # 定时器
        self._timer = QTimer()
        self._timer.timeout.connect(self._on_timer_triggered)

        # 状态
        self._is_running = False
        self._selected_slot = -1  # 当前选中的槽位索引（-1表示未选中）
        self._stats = {
            "total": 0,
            "success": 0,
            "fail": 0
        }

        # 组件
        self._capture = None
        self._ocr_engine = None
        self._matcher = None
        self._sprite_rows = []

        # 初始化6个空槽位
        self._init_empty_slots()

        # 按钮事件
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._cover_recognize_btn.clicked.connect(self._on_cover_recognize)
        self._cover_manual_btn.clicked.connect(self._on_cover_manual)

        # 全屏状态
        self._is_fullscreen_results = False

    def _toggle_fullscreen_results(self):
        """切换识别结果区全屏显示"""
        self._is_fullscreen_results = not self._is_fullscreen_results

        if self._is_fullscreen_results:
            # 隐藏顶部区域
            self._control_group.hide()
            self._status_group.hide()
            self._screenshot_group.hide()
            self._fullscreen_btn.setText("退出全屏")
        else:
            # 显示顶部区域
            self._control_group.show()
            self._status_group.show()
            self._screenshot_group.show()
            self._fullscreen_btn.setText("全屏展示")

    def _init_empty_slots(self):
        """初始化6个空槽位"""
        for i in range(6):
            row = SpriteRowWidget(i, sprite_info=None)
            row.clicked.connect(self._on_slot_clicked)
            self._sprite_rows.append(row)
            self._results_layout.addWidget(row)

    def _on_slot_clicked(self, index: int):
        """槽位被点击"""
        # 取消之前的选中
        for i, row in enumerate(self._sprite_rows):
            row.set_selected(i == index)

        self._selected_slot = index
        self._cover_recognize_btn.setEnabled(True)
        self._cover_manual_btn.setEnabled(True)
        self._update_status(f"已选中槽位 {index + 1}")

    def _on_cover_recognize(self):
        """识别覆盖当前槽位"""
        if self._selected_slot < 0:
            return

        self._update_status(f"正在识别槽位 {self._selected_slot + 1}...")
        self._perform_recognition(for_slot=self._selected_slot)

    def _on_cover_manual(self):
        """手动输入覆盖当前槽位"""
        if self._selected_slot < 0:
            return

        dialog = SpriteSearchDialog(self.session, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sprite_info = dialog.get_selected_sprite()
            if sprite_info:
                self._sprite_rows[self._selected_slot].set_sprite(sprite_info)
                self._update_status(f"槽位 {self._selected_slot + 1} 已设置为 {sprite_info.name}")

    def _on_start_clicked(self):
        """开始识别按钮点击"""
        if self._auto_mode_radio.isChecked():
            self.start_auto_recognition()
        else:
            self._perform_single_recognition()

    def _on_stop_clicked(self):
        """停止按钮点击"""
        self.stop_auto_recognition()

    def start_auto_recognition(self):
        """启动自动识别"""
        if self._is_running:
            return

        self._is_running = True
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._update_status("自动识别中...")

        interval = self._interval_spin.value() * 1000
        self._timer.start(interval)
        print(f"[配队识别] 启动自动识别，间隔: {interval//1000}秒")

        # 立即执行一次
        self._perform_recognition()

    def stop_auto_recognition(self):
        """停止自动识别"""
        self._is_running = False
        self._timer.stop()
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._update_status("已停止")
        print("[配队识别] 停止自动识别")

    def _on_timer_triggered(self):
        """定时器触发"""
        if not self._is_running:
            return
        print("[配队识别] 定时器触发，执行识别")
        self._perform_recognition()

    def _perform_single_recognition(self):
        """执行单次识别"""
        self._update_status("识别中...")
        print("[配队识别] 开始单次识别")
        self._perform_recognition()

    def _perform_recognition(self, for_slot: int = -1):
        """执行一次识别

        Args:
            for_slot: 指定覆盖的槽位索引，-1表示填充所有空槽位
        """
        self._stats["total"] += 1
        print(f"[配队识别] ========== 开始第 {self._stats['total']} 次识别 ==========")

        try:
            # 1. 初始化组件（懒加载）
            try:
                if self._capture is None:
                    print("[配队识别] 检查: 需要初始化截图组件")
                    self._capture = ScreenCapture(monitor_index=OCR_CONFIG["monitor_index"])
                    print("[配队识别] 初始化屏幕截图组件 - 完成")
                else:
                    print("[配队识别] 检查: 截图组件已存在")
            except Exception as e:
                logger.error(f"[配队识别] 截图组件初始化失败: {str(e)}", exc_info=True)
                raise

            try:
                if self._ocr_engine is None:
                    print("[配队识别] 检查: 需要初始化 OCR 引擎")
                    print("[配队识别] 开始初始化 OCR 引擎...")
                    self._ocr_engine = OCREngine()
                    print("[配队识别] 初始化 OCR 引擎 - 完成")
                else:
                    print("[配队识别] 检查: OCR 引擎已存在")
            except Exception as e:
                logger.error(f"[配队识别] OCR 引擎初始化失败: {str(e)}", exc_info=True)
                raise

            try:
                if self._matcher is None:
                    print("[配队识别] 检查: 需要初始化模糊匹配器")
                    self._matcher = SpriteMatcher(self.session)
                    print("[配队识别] 初始化模糊匹配器 - 完成")
                else:
                    print("[配队识别] 检查: 模糊匹配器已存在")
            except Exception as e:
                logger.error(f"[配队识别] 模糊匹配器初始化失败: {str(e)}", exc_info=True)
                raise

            # 2. 截图
            region_type = "top_right" if self._top_right_radio.isChecked() else "team_list"
            region = CAPTURE_REGIONS[region_type]
            print(f"[配队识别] 截图区域: {region_type}, 坐标: x={region['x']:.4f}, y={region['y']:.4f}, w={region['width']:.4f}, h={region['height']:.4f}")

            screenshot = self._capture.capture_region_percent(
                region["x"], region["y"], region["width"], region["height"]
            )
            print(f"[配队识别] 截图完成，图像尺寸: {screenshot.shape}")

            # 更新截图预览
            self._update_screenshot_preview(screenshot)

            # 3. OCR 识别
            print("[配队识别] 开始 OCR 文字识别...")
            ocr_results = self._ocr_engine.recognize_text_only(screenshot)
            print(f"[配队识别] OCR 识别完成，识别到 {len(ocr_results)} 个文本: {ocr_results}")

            if not ocr_results:
                logger.warning("[配队识别] 未识别到文字")
                self._show_empty_result("未识别到文字")
                self._stats["fail"] += 1
                self._update_stats()
                return

            # 4. 模糊匹配
            print("[配队识别] 开始模糊匹配精灵名称...")
            matched_sprites = self._matcher.match_all(ocr_results, OCR_CONFIG["fuzzy_threshold"])

            # 过滤未匹配的结果
            valid_names = [m["matched_name"] for m in matched_sprites if m["matched_name"]]
            print(f"[配队识别] 模糊匹配结果: {matched_sprites}")

            if not valid_names:
                logger.warning(f"[配队识别] 未能匹配到精灵，阈值: {OCR_CONFIG['fuzzy_threshold']}")
                self._show_empty_result("未能匹配到精灵")
                self._stats["fail"] += 1
                self._update_stats()
                return

            # 5. 查询数据库
            print(f"[配队识别] 开始查询数据库，精灵名称: {valid_names}")
            sprite_details = []
            for name in valid_names:
                info = get_sprite_detail_by_name(self.session, name)
                if info:
                    sprite_details.append(info)
                    print(f"[配队识别] 查询精灵成功: {name}, 技能数: {len(info.skills)}")
                else:
                    logger.warning(f"[配队识别] 数据库中未找到精灵: {name}")

            if not sprite_details:
                logger.warning("[配队识别] 数据库中未找到任何匹配的精灵")
                self._show_empty_result("数据库中未找到精灵")
                self._stats["fail"] += 1
                self._update_stats()
                return

            # 6. 更新 UI
            print(f"[配队识别] 识别成功，共 {len(sprite_details)} 只精灵")
            self._update_results(sprite_details, for_slot)
            self._stats["success"] += 1
            self._update_stats()

            if not self._is_running:  # 单次模式
                self._update_status("识别成功")
            print(f"[配队识别] ========== 第 {self._stats['total']} 次识别完成 ==========")

        except Exception as e:
            logger.error(f"[配队识别] 识别过程出错: {str(e)}", exc_info=True)
            if for_slot >= 0:
                self._update_status(f"识别失败: {str(e)}")
            else:
                self._show_empty_result(f"识别失败: {str(e)}")
            self._stats["fail"] += 1
            self._update_stats()
            if not self._is_running:
                self._update_status("识别失败")

    def _show_empty_result(self, message: str):
        """显示空结果提示"""
        # 显示消息（不清空现有槽位）
        QMessageBox.information(self, "提示", message)

    def _update_screenshot_preview(self, image: np.ndarray):
        """更新截图预览"""
        try:
            # 将 numpy 数组 (BGR) 转换为 QPixmap
            height, width, channel = image.shape
            bytes_per_line = 3 * width

            # BGR -> RGB 转换
            # mss 返回的是 BGR 格式，需要转换为 RGB
            image_rgb = image[:, :, ::-1]  # 反转通道顺序 BGR -> RGB

            # 转换为 bytes
            image_bytes = image_rgb.tobytes()

            # 创建 QImage (RGB 格式)
            q_img = QImage(
                image_bytes,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )

            # 转换为 QPixmap
            pixmap = QPixmap.fromImage(q_img)

            # 缩放以适应显示区域
            label_size = self._screenshot_label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                scaled_pixmap = pixmap.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._screenshot_label.setPixmap(scaled_pixmap)
            else:
                # 如果 label 还没有大小，使用默认大小
                scaled_pixmap = pixmap.scaled(
                    QSize(400, 150),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._screenshot_label.setPixmap(scaled_pixmap)

            self._screenshot_label.setText("")  # 清除文字
        except Exception as e:
            self._screenshot_label.setText(f"截图显示失败: {str(e)}")
            self._screenshot_label.clear()  # 清除 pixmap 而不是设置 None

    def _update_results(self, sprite_infos: list[SpriteInfo], for_slot: int = -1):
        """更新识别结果

        Args:
            sprite_infos: 识别到的精灵列表
            for_slot: 指定覆盖的槽位索引，-1表示填充空槽位
        """
        if for_slot >= 0:
            # 覆盖指定槽位
            if sprite_infos:
                self._sprite_rows[for_slot].set_sprite(sprite_infos[0])
                self._update_status(f"槽位 {for_slot + 1} 已设置为 {sprite_infos[0].name}")
            else:
                self._update_status(f"槽位 {for_slot + 1} 识别失败")
        else:
            # 填充空槽位
            empty_slots = [i for i, row in enumerate(self._sprite_rows) if row.is_empty()]
            for i, sprite_info in enumerate(sprite_infos):
                if i < len(empty_slots):
                    slot_idx = empty_slots[i]
                    self._sprite_rows[slot_idx].set_sprite(sprite_info)
                elif len(self._sprite_rows) < 6:
                    # 如果还有空位，添加新行
                    row = SpriteRowWidget(len(self._sprite_rows), sprite_info)
                    row.clicked.connect(self._on_slot_clicked)
                    self._sprite_rows.append(row)
                    self._results_layout.addWidget(row)
            self._results_layout.addWidget(row)

    def _update_status(self, status: str):
        """更新状态"""
        self._status_label.setText(f"状态：{status}")

    def _update_stats(self):
        """更新统计"""
        total = self._stats["total"]
        success = self._stats["success"]
        fail = self._stats["fail"]

        self._count_label.setText(f"识别次数：{total}")

        if total > 0:
            rate = int((success / total) * 100)
        else:
            rate = 0
        self._success_label.setText(f"成功率：{rate}%")

    def closeEvent(self, event):
        """关闭事件"""
        if self._is_running:
            self.stop_auto_recognition()
        event.accept()
