"""屏幕截图模块 - 基于 mss 的屏幕截图功能"""

import numpy as np
from typing import Optional
import mss


class ScreenCapture:
    """屏幕截图工具类"""

    def __init__(self, monitor_index: int = 0):
        """
        初始化屏幕截图工具

        Args:
            monitor_index: 显示器索引，0 为主显示器
        """
        self._monitor_index = monitor_index
        self._sct = mss.mss()

    def capture_region(self, x: int, y: int, width: int, height: int,
                      monitor_index: Optional[int] = None) -> np.ndarray:
        """
        截取指定屏幕区域

        Args:
            x: 区域左上角 X 坐标（相对于显示器）
            y: 区域左上角 Y 坐标（相对于显示器）
            width: 区域宽度
            height: 区域高度
            monitor_index: 显示器索引（如果为 None，使用初始化时的索引）

        Returns:
            numpy 数组格式的图像（BGR 格式）
        """
        monitor = monitor_index if monitor_index is not None else self._monitor_index

        # 获取显示器信息
        mon = self._sct.monitors[monitor + 1]  # monitors[0] 是所有显示器的并集

        # 计算截图区域（相对于显示器的绝对坐标）
        region = {
            "left": mon["left"] + x,
            "top": mon["top"] + y,
            "width": width,
            "height": height
        }

        # 截图
        screenshot = self._sct.grab(region)

        # 转换为 numpy 数组（BGRA）
        img = np.array(screenshot)

        # 转换为 BGR 格式（去掉 Alpha 通道）
        if img.shape[2] == 4:
            img = img[:, :, :3]

        return img

    def capture_region_percent(self, x_percent: float, y_percent: float,
                               width_percent: float, height_percent: float,
                               monitor_index: Optional[int] = None) -> np.ndarray:
        """
        按屏幕百分比截取区域

        Args:
            x_percent: 区域左上角 X 坐标百分比（0-1）
            y_percent: 区域左上角 Y 坐标百分比（0-1）
            width_percent: 区域宽度百分比（0-1）
            height_percent: 区域高度百分比（0-1）
            monitor_index: 显示器索引

        Returns:
            numpy 数组格式的图像
        """
        monitor = monitor_index if monitor_index is not None else self._monitor_index
        mon = self._sct.monitors[monitor + 1]

        # 计算绝对坐标
        x = int(mon["width"] * x_percent)
        y = int(mon["height"] * y_percent)
        width = int(mon["width"] * width_percent)
        height = int(mon["height"] * height_percent)

        return self.capture_region(x, y, width, height, monitor_index)

    def get_monitor_size(self, monitor_index: Optional[int] = None) -> tuple[int, int]:
        """
        获取显示器尺寸

        Args:
            monitor_index: 显示器索引

        Returns:
            (width, height)
        """
        monitor = monitor_index if monitor_index is not None else self._monitor_index
        mon = self._sct.monitors[monitor + 1]
        return mon["width"], mon["height"]
