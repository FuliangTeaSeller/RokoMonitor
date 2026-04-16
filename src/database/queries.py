"""精灵/技能查询接口"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.database.models import Attribute, Skill, Sprite, SpriteAttribute, SpriteSkill


@dataclass
class SkillInfo:
    """技能简要信息"""
    id: int
    name: str
    attribute: str
    category: str
    power: Optional[int]
    energy_consumption: int
    description: Optional[str]
    image_path: Optional[str] = None


@dataclass
class SpriteInfo:
    """精灵完整信息（含属性与技能池）"""
    id: int
    name: str
    image_path: Optional[str] = None
    attributes: list[str] = field(default_factory=list)
    skills: list[SkillInfo] = field(default_factory=list)


def search_sprites_by_name(session: Session, keyword: str) -> list[SpriteInfo]:
    """按名称模糊搜索精灵，返回精灵基本信息（不含技能池）"""
    stmt = select(Sprite).where(Sprite.name.like(f"%{keyword}%"))
    sprites = session.execute(stmt).scalars().all()

    results = []
    for sp in sprites:
        attrs = _get_sprite_attributes(session, sp.id)
        results.append(SpriteInfo(id=sp.id, name=sp.name, image_path=sp.image_path, attributes=attrs))
    return results


def get_sprite_detail(session: Session, sprite_id: int) -> Optional[SpriteInfo]:
    """获取精灵完整详情（属性 + 技能池）"""
    sp = session.get(Sprite, sprite_id)
    if sp is None:
        return None

    attrs = _get_sprite_attributes(session, sp.id)
    skills = _get_sprite_skills(session, sp.id)
    return SpriteInfo(id=sp.id, name=sp.name, attributes=attrs, skills=skills)


def get_sprite_detail_by_name(session: Session, name: str) -> Optional[SpriteInfo]:
    """按名称精确查询精灵详情"""
    stmt = select(Sprite).where(Sprite.name == name)
    sp = session.execute(stmt).scalar_one_or_none()
    if sp is None:
        return None
    return get_sprite_detail(session, sp.id)


def get_all_attributes(session: Session) -> list[Attribute]:
    """获取全部属性"""
    return list(session.execute(select(Attribute)).scalars().all())


def get_all_skills(session: Session) -> list[Skill]:
    """获取全部技能"""
    return list(session.execute(select(Skill)).scalars().all())


def get_all_sprites(session: Session) -> list[Sprite]:
    """获取全部精灵"""
    return list(session.execute(select(Sprite)).scalars().all())


def add_sprite(session: Session, name: str, attribute_ids: list[int], skill_ids: list[int]) -> Sprite:
    """新增精灵"""
    sp = Sprite(name=name)
    session.add(sp)
    session.flush()

    for aid in attribute_ids:
        session.add(SpriteAttribute(sprite_id=sp.id, attribute_id=aid))
    for sid in skill_ids:
        session.add(SpriteSkill(sprite_id=sp.id, skill_id=sid))

    session.commit()
    return sp


def add_skill(
    session: Session,
    name: str,
    attribute_id: int,
    category: str,
    energy_consumption: int,
    power: Optional[int] = None,
    description: Optional[str] = None,
) -> Skill:
    """新增技能"""
    skill = Skill(
        name=name,
        attribute_id=attribute_id,
        category=category,
        energy_consumption=energy_consumption,
        power=power,
        description=description,
    )
    session.add(skill)
    session.commit()
    return skill


def _get_sprite_attributes(session: Session, sprite_id: int) -> list[str]:
    stmt = (
        select(Attribute.name)
        .join(SpriteAttribute, SpriteAttribute.attribute_id == Attribute.id)
        .where(SpriteAttribute.sprite_id == sprite_id)
    )
    return list(session.execute(stmt).scalars().all())


def _get_sprite_skills(session: Session, sprite_id: int) -> list[SkillInfo]:
    stmt = (
        select(Skill)
        .join(SpriteSkill, SpriteSkill.skill_id == Skill.id)
        .where(SpriteSkill.sprite_id == sprite_id)
    )
    skills = session.execute(stmt).scalars().all()
    return [
        SkillInfo(
            id=s.id,
            name=s.name,
            attribute=s.attribute.name,
            category=s.category,
            power=s.power,
            energy_consumption=s.energy_consumption,
            description=s.description,
            image_path=s.image_path,
        )
        for s in skills
    ]
