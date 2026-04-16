"""文本模糊匹配 - OCR 结果匹配到数据库中的精灵名称"""

from typing import Optional, List
from sqlalchemy.orm import Session
from thefuzz import fuzz, process


class SpriteMatcher:
    """精灵名称模糊匹配器"""

    def __init__(self, session: Session):
        """
        初始化匹配器

        Args:
            session: 数据库会话
        """
        self.session = session
        self._sprite_names = self._load_all_sprite_names()

    def _load_all_sprite_names(self) -> list[str]:
        """加载所有精灵名称用于匹配"""
        from src.database.queries import get_all_sprites
        sprites = get_all_sprites(self.session)
        return [sp.name for sp in sprites]

    def match(self, ocr_text: str, threshold: int = 70) -> tuple[Optional[str], int]:
        """
        模糊匹配 OCR 识别的精灵名称

        Args:
            ocr_text: OCR 识别的文本
            threshold: 相似度阈值（0-100），默认 70

        Returns:
            (匹配的精灵名称, 相似度分数)，如果未匹配则为 (None, 0)
        """
        if not ocr_text or not ocr_text.strip():
            return None, 0

        # 去除空白字符
        ocr_text = ocr_text.strip()

        # 使用模糊匹配算法
        result = process.extractOne(
            ocr_text,
            self._sprite_names,
            scorer=fuzz.WRatio
        )

        if result and result[1] >= threshold:
            return result[0], result[1]
        return None, 0

    def match_all(self, ocr_texts: List[str], threshold: int = 70) -> List[dict]:
        """
        批量匹配多个 OCR 结果

        Args:
            ocr_texts: OCR 识别的文本列表
            threshold: 相似度阈值（0-100）

        Returns:
            匹配结果列表，每项包含：
            - ocr_text: 原始 OCR 文本
            - matched_name: 匹配到的精灵名称（None 表示未匹配）
            - score: 相似度分数
        """
        results = []
        for text in ocr_texts:
            if text and text.strip():
                matched_name, score = self.match(text, threshold)
            else:
                matched_name, score = None, 0

            results.append({
                "ocr_text": text,
                "matched_name": matched_name,
                "score": score
            })
        return results

    def get_all_sprite_names(self) -> list[str]:
        """获取所有精灵名称"""
        return self._sprite_names.copy()
