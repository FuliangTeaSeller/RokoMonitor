"""OCR 引擎封装 - 基于 PaddleOCR 3.2+ 的文字识别"""

import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR 引擎封装类"""

    _instance: Optional["OCREngine"] = None

    def __new__(cls):
        """单例模式，确保只初始化一次 OCR 引擎"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            logger.info("[OCREngine] 创建新实例")
        else:
            logger.debug("[OCREngine] 返回已存在的实例")
        return cls._instance

    def __init__(self):
        """初始化 OCR 引擎"""
        logger.info(f"[OCREngine] __init__ 被调用, _initialized={self._initialized}")

        if self._initialized:
            logger.info("[OCREngine] 已初始化，跳过")
            return

        try:
            logger.info("[OCREngine] 开始导入 PaddleOCR...")
            from paddleocr import PaddleOCR

            # 使用 PaddleOCR 3.2+ 官方推荐的基础配置
            # 参考: https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/doc/doc_ch/inference_ppocr.md
            logger.info("[OCREngine] 开始创建 PaddleOCR 实例...")
            self._ocr = PaddleOCR(
                use_doc_orientation_classify=False,  # 是否使用文档方向分类
                use_doc_unwarping=False,              # 是否使用文档去扭曲
                use_textline_orientation=False            # 是否使用文本行方向分类
            )
            self._initialized = True
            logger.info("[OCREngine] PaddleOCR 初始化完成")
        except ImportError as e:
            logger.error(f"[OCREngine] 导入错误: {e}")
            raise ImportError(
                "PaddleOCR 未安装。请运行: pip install paddleocr"
            ) from e

    def recognize(self, image: np.ndarray) -> list[dict]:
        """
        识别图片中的文字

        Args:
            image: numpy 数组格式的图像（BGR 格式）

        Returns:
            识别结果列表，每项包含：
            - text: 识别的文本
            - confidence: 置信度（0-1）
            - bbox: 文本框坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        """
        if not self._initialized:
            raise RuntimeError("OCR 引擎未初始化")

        # 使用 predict 方法（PaddleOCR 3.2+）
        result = self._ocr.predict(image)
        # for res in result:
        #     res.print()
            
        # 解析结果
        texts = []
        for res in result:

            # 提取识别结果
            rec_texts = res.get('rec_texts', [])
            rec_scores = res.get('rec_scores', [])
            rec_polys = res.get('rec_polys', [])

            # 组合结果
            for i, text in enumerate(rec_texts):
                if not text or not text.strip():
                    continue

                texts.append({
                    "text": text.strip(),
                    "confidence": float(rec_scores[i]) if i < len(rec_scores) else 0.0,
                    "bbox": rec_polys[i].tolist() if i < len(rec_polys) else []
                })

        return texts

    def recognize_text_only(self, image: np.ndarray) -> list[str]:
        """
        识别图片中的文字，只返回文本列表

        Args:
            image: numpy 数组格式的图像

        Returns:
            文本列表
        """
        results = self.recognize(image)
        return [r["text"] for r in results]
