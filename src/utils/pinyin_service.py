"""拼音首字母缓存服务"""

from functools import lru_cache
from typing import Optional

from pypinyin import lazy_pinyin, Style


class PinyinService:
    """拼音首字母缓存服务（单例模式）"""

    _instance: Optional['PinyinService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sprite_cache: dict[int, str] = {}
            cls._instance._skill_cache: dict[int, str] = {}
            cls._instance._sprite_name_to_id: dict[str, int] = {}
            cls._instance._skill_name_to_id: dict[str, int] = {}
        return cls._instance

    @staticmethod
    @lru_cache(maxsize=4096)
    def get_initials(text: str) -> str:
        """获取字符串的拼音首字母

        例: "水蓝蓝" -> "sll", "先发制人" -> "xfzr"
        """
        initials = lazy_pinyin(text, style=Style.INITIALS, errors='default')
        return ''.join(initials).lower()

    @staticmethod
    def match(text: str, query: str) -> bool:
        """检查 query 是否匹配 text 的名称或拼音首字母"""
        text_lower = text.lower()
        query_lower = query.lower()
        initials = PinyinService.get_initials(text)
        return query_lower in text_lower or query_lower in initials

    def init_sprite_cache(self, sprites: list) -> None:
        """初始化精灵拼音缓存"""
        self._sprite_cache.clear()
        self._sprite_name_to_id.clear()
        for sp in sprites:
            self._sprite_cache[sp.id] = self.get_initials(sp.name)
            self._sprite_name_to_id[sp.name] = sp.id

    def init_skill_cache(self, skills: list) -> None:
        """初始化技能拼音缓存"""
        self._skill_cache.clear()
        self._skill_name_to_id.clear()
        for sk in skills:
            self._skill_cache[sk.id] = self.get_initials(sk.name)
            self._skill_name_to_id[sk.name] = sk.id

    def add_sprite(self, sprite_id: int, name: str) -> None:
        """添加或更新精灵缓存"""
        self._sprite_cache[sprite_id] = self.get_initials(name)
        self._sprite_name_to_id[name] = sprite_id

    def add_skill(self, skill_id: int, name: str) -> None:
        """添加或更新技能缓存"""
        self._skill_cache[skill_id] = self.get_initials(name)
        self._skill_name_to_id[name] = skill_id

    def search_sprites(self, query: str) -> list[int]:
        """搜索匹配的精灵ID列表"""
        query_lower = query.lower()
        return [
            sprite_id for name, sprite_id in self._sprite_name_to_id.items()
            if query_lower in name.lower() or query_lower in self.get_initials(name)
        ]

    def search_skills(self, query: str) -> list[int]:
        """搜索匹配的技能ID列表"""
        query_lower = query.lower()
        return [
            skill_id for name, skill_id in self._skill_name_to_id.items()
            if query_lower in name.lower() or query_lower in self.get_initials(name)
        ]
