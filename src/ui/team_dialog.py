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


class SkillDetailItem(QPushButton):
    """技能详情卡片（右侧技能项）"""

    def __init__(self, skill: SkillInfo, parent=None):
        super().__init__(parent)
        self._skill = skill
        self._init_ui()

    def _init_ui(self):
        skill = self._skill
        self.setFixedSize(200, 80)
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
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # 技能图标
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(32, 32)
        if skill.image_path:
            icon = load_icon(skill.image_path, size=(32, 32))
            if icon:
                self._icon_label.setPixmap(icon)
        layout.addWidget(self._icon_label)

        # 技能信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 名称
        name_label = QLabel(skill.name)
        name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #cdd6f4; background: transparent;")
        info_layout.addWidget(name_label)

        # 属性 + 能耗
        attr_energy = f"[{skill.attribute}] 能耗:{skill.energy_consumption}"
        attr_label = QLabel(attr_energy)
        attr_label.setFont(QFont("Microsoft YaHei", 9))
        attr_label.setStyleSheet("color: #89b4fa; background: transparent;")
        info_layout.addWidget(attr_label)

        # 描述（截断）
        if skill.description:
            desc = skill.description[:20] + "..." if len(skill.description) > 20 else skill.description
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("Microsoft YaHei", 8))
            desc_label.setStyleSheet("color: #a6adc8; background: transparent;")
            info_layout.addWidget(desc_label)

        layout.addLayout(info_layout)


class SpriteRowWidget(QFrame):
    """精灵-技能行组件（左右一行）"""

    def __init__(self, sprite_info: SpriteInfo, parent=None):
        super().__init__(parent)
        self._sprite_info = sprite_info
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

        # 左侧：精灵信息
        left_frame = QFrame()
        left_frame.setFixedWidth(150)
        left_frame.setStyleSheet("""
            QFrame {
                background-color: #313244;
                border: none;
            }
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(4)

        # 精灵图标
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        if self._sprite_info.image_path:
            icon = load_icon(self._sprite_info.image_path, size=(48, 48))
            if icon:
                icon_label.setPixmap(icon)
        left_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 精灵名称
        name_label = QLabel(self._sprite_info.name)
        name_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #cdd6f4; background: transparent;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(name_label)

        # 属性
        if self._sprite_info.attributes:
            attr_text = " / ".join(self._sprite_info.attributes)
        else:
            attr_text = "未知"
        attr_label = QLabel(attr_text)
        attr_label.setFont(QFont("Microsoft YaHei", 9))
        attr_label.setStyleSheet("color: #89b4fa; background: transparent;")
        attr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(attr_label)

        left_layout.addStretch()
        layout.addWidget(left_frame)

        # 右侧：技能列表（横向滚动）
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("""
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

        skills_container = QWidget()
        skills_layout = QHBoxLayout(skills_container)
        skills_layout.setContentsMargins(10, 10, 10, 10)
        skills_layout.setSpacing(10)
        skills_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        if self._sprite_info.skills:
            for skill in self._sprite_info.skills:
                item = SkillDetailItem(skill)
                item.clicked.connect(lambda checked, s=skill: self._show_skill_detail(s))
                skills_layout.addWidget(item)
        else:
            empty_label = QLabel("暂无技能数据")
            empty_label.setStyleSheet("color: #a6adc8; font-size: 12px; background: transparent;")
            skills_layout.addWidget(empty_label)

        skills_layout.addStretch()
        right_scroll.setWidget(skills_container)
        layout.addWidget(right_scroll, 1)

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
        self._sprite_rows = []

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
        # 清空现有行
        for row in self._sprite_rows:
            row.deleteLater()
        self._sprite_rows.clear()

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
        # 清空现有行
        for row in self._sprite_rows:
            row.deleteLater()
        self._sprite_rows.clear()

        # 清空布局
        while self._results_layout.count():
            child = self._results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 添加新行
        for sprite_info in sprite_infos:
            row = SpriteRowWidget(sprite_info)
            self._sprite_rows.append(row)
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
