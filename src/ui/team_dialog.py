"""配队识别对话框"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QRadioButton, QButtonGroup, QSpinBox, QScrollArea, QWidget,
    QGridLayout, QMessageBox, QFrame, QFrame as QtFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage
import numpy as np

from sqlalchemy.orm import Session

from src.database.queries import get_sprite_detail_by_name, SpriteInfo, SkillInfo
from src.config import CAPTURE_REGIONS, OCR_CONFIG
from src.capture.screen_capture import ScreenCapture
from src.ocr.engine import OCREngine
from src.ocr.text_match import SpriteMatcher
from src.ui.image_utils import load_icon

# 配置日志
logger = logging.getLogger(__name__)


class SpriteCard(QWidget):
    """精灵信息卡片"""

    def __init__(self, sprite_info: SpriteInfo, parent=None):
        super().__init__(parent)
        self._sprite_info = sprite_info
        self._expanded = False
        self._visible_count = 8  # 默认显示的技能数量
        self._skill_buttons = []
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 头部：精灵名称 + 属性
        header = QHBoxLayout()
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(48, 48)
        header.addWidget(self._icon_label)

        name_attr_layout = QVBoxLayout()
        self._name_label = QLabel()
        self._name_label.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        name_attr_layout.addWidget(self._name_label)

        self._attr_label = QLabel()
        self._attr_label.setFont(QFont("Microsoft YaHei", 10))
        name_attr_layout.addWidget(self._attr_label)

        header.addLayout(name_attr_layout)
        header.addStretch()

        layout.addLayout(header)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #45475a;")
        layout.addWidget(line)

        # 技能网格
        self._skill_grid = QGridLayout()
        self._skill_grid.setSpacing(8)
        layout.addLayout(self._skill_grid)

        # 展开/折叠按钮
        self._toggle_btn = QPushButton("展开全部")
        self._toggle_btn.clicked.connect(self._toggle_expand)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #89b4fa;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
        """)
        layout.addWidget(self._toggle_btn)

    def _load_data(self):
        """加载数据"""
        info = self._sprite_info

        # 加载图标
        if info.image_path:
            icon = load_icon(info.image_path, size=(44, 44))
            if icon:
                self._icon_label.setPixmap(icon)

        self._name_label.setText(info.name)
        if info.attributes:
            self._attr_label.setText(" / ".join(info.attributes))
        else:
            self._attr_label.setText("未知属性")

        # 加载技能
        self._load_skills()

    def _load_skills(self):
        """加载技能按钮"""
        # 清空现有按钮
        for btn in self._skill_buttons:
            btn.deleteLater()
        self._skill_buttons.clear()

        skills = self._sprite_info.skills
        if not skills:
            empty_label = QLabel("暂无技能数据")
            empty_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
            self._skill_grid.addWidget(empty_label, 0, 0)
            self._toggle_btn.hide()
            return

        display_count = len(skills) if self._expanded else min(len(skills), self._visible_count)

        for i in range(display_count):
            skill = skills[i]
            btn = SkillButton(skill)
            btn.clicked.connect(lambda checked, s=skill: self._show_skill_detail(s))
            self._skill_buttons.append(btn)

            row = i // 2
            col = i % 2
            self._skill_grid.addWidget(btn, row, col)

        # 更新折叠按钮
        if len(skills) <= self._visible_count:
            self._toggle_btn.hide()
        else:
            total_count = len(skills)
            self._toggle_btn.setText("折叠" if self._expanded else f"展开全部({total_count}个技能)")
            self._toggle_btn.show()

    def _toggle_expand(self):
        """切换展开/折叠"""
        self._expanded = not self._expanded
        self._load_skills()

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


class SkillButton(QPushButton):
    """技能按钮"""

    def __init__(self, skill: SkillInfo, parent=None):
        super().__init__(parent)
        self._skill = skill
        self._init_ui()

    def _init_ui(self):
        skill = self._skill
        text = f"{skill.name}"
        if skill.power:
            text += f"\n威力: {skill.power}"
        else:
            text += "\n变化类"
        text += f"\n[{skill.attribute}]"

        self.setText(text)
        self.setMinimumHeight(65)
        self.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                text-align: left;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
                border-color: #89b4fa;
            }
            QPushButton:pressed {
                background-color: #1e1e2e;
            }
        """)


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
        self.setMinimumSize(700, 600)
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

        # 识别控制区
        control_group = self._create_control_group()
        layout.addWidget(control_group)

        # 截图显示区
        screenshot_group = self._create_screenshot_group()
        layout.addWidget(screenshot_group)

        # 识别结果区
        results_group = self._create_results_group()
        layout.addWidget(results_group, 1)  # expand=1

        # 状态信息区
        status_group = self._create_status_group()
        layout.addWidget(status_group)

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
        btn_layout.addWidget(self._start_btn)
        btn_layout.addWidget(self._stop_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return frame

    def _create_screenshot_group(self) -> QtFrame:
        """创建截图显示区"""
        frame = QtFrame()
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
        self._screenshot_label.setMinimumHeight(150)
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

        # 标题
        title = QLabel("识别结果")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

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
        frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout = QHBoxLayout(frame)

        self._status_label = QLabel("状态：就绪")
        self._count_label = QLabel("识别次数：0")
        self._success_label = QLabel("成功率：0%")

        layout.addWidget(self._status_label)
        layout.addSpacing(20)
        layout.addWidget(self._count_label)
        layout.addSpacing(20)
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
        self._stats = {
            "total": 0,
            "success": 0,
            "fail": 0
        }

        # 组件
        self._capture = None
        self._ocr_engine = None
        self._matcher = None
        self._sprite_cards = []

        # 按钮事件
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)

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

    def _perform_recognition(self):
        """执行一次识别"""
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
            self._update_results(sprite_details)
            self._stats["success"] += 1
            self._update_stats()

            if not self._is_running:  # 单次模式
                self._update_status("识别成功")
            print(f"[配队识别] ========== 第 {self._stats['total']} 次识别完成 ==========")

        except Exception as e:
            logger.error(f"[配队识别] 识别过程出错: {str(e)}", exc_info=True)
            self._show_empty_result(f"识别失败: {str(e)}")
            self._stats["fail"] += 1
            self._update_stats()
            if not self._is_running:
                self._update_status("识别失败")

    def _show_empty_result(self, message: str):
        """显示空结果"""
        # 清空现有卡片
        for card in self._sprite_cards:
            card.deleteLater()
        self._sprite_cards.clear()

        # 显示消息
        empty_label = QLabel(message)
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #f38ba8; font-size: 14px; padding: 40px;")
        self._results_layout.addWidget(empty_label)

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

    def _update_results(self, sprite_infos: list[SpriteInfo]):
        """更新识别结果"""
        # 清空现有卡片
        for card in self._sprite_cards:
            card.deleteLater()
        self._sprite_cards.clear()

        # 清空布局
        while self._results_layout.count():
            child = self._results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 添加新卡片
        for sprite_info in sprite_infos:
            card = SpriteCard(sprite_info)
            self._sprite_cards.append(card)
            self._results_layout.addWidget(card)

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
