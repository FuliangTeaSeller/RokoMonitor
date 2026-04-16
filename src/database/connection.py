"""数据库连接、建表与种子数据"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.config import DATABASE_PATH
from src.database.models import Base, Attribute, Skill, Sprite, SpriteAttribute, SpriteSkill

engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)


def init_db():
    """建表并插入 mock 种子数据"""
    Base.metadata.create_all(engine)
    _seed_mock_data()


def get_session() -> Session:
    return Session(engine)


def _seed_mock_data():
    """仅在数据库为空时插入种子数据"""
    with Session(engine) as session:
        if session.query(Attribute).first() is not None:
            return

        # --- 属性 ---
        attrs = [
            Attribute(id=1, name="火"),
            Attribute(id=2, name="水"),
            Attribute(id=3, name="草"),
            Attribute(id=4, name="龙"),
            Attribute(id=5, name="冰"),
            Attribute(id=6, name="普通"),
        ]
        session.add_all(attrs)

        # --- 技能 ---
        skills = [
            Skill(id=1,  name="烈焰冲击",   energy_consumption=3, category="物攻", attribute_id=1, power=80,  description="以烈焰之力冲撞对手"),
            Skill(id=2,  name="火焰旋风",   energy_consumption=4, category="魔攻", attribute_id=1, power=90,  description="召唤火焰旋风席卷对手"),
            Skill(id=3,  name="鬼火",       energy_consumption=2, category="变化", attribute_id=1, power=None, description="令对手陷入灼烧状态"),
            Skill(id=4,  name="水炮",       energy_consumption=4, category="魔攻", attribute_id=2, power=95,  description="向对手发射高压水炮"),
            Skill(id=5,  name="水流喷射",   energy_consumption=2, category="物攻", attribute_id=2, power=60,  description="以极速水流攻击对手，必定先手"),
            Skill(id=6,  name="祈雨",       energy_consumption=2, category="变化", attribute_id=2, power=None, description="改变天气为雨天"),
            Skill(id=7,  name="日光束",     energy_consumption=4, category="魔攻", attribute_id=3, power=100, description="聚集阳光释放强力光束"),
            Skill(id=8,  name="叶刃",       energy_consumption=3, category="物攻", attribute_id=3, power=75,  description="以锋利的叶片斩击对手"),
            Skill(id=9,  name="龙之波动",   energy_consumption=4, category="魔攻", attribute_id=4, power=85,  description="释放龙的波动冲击对手"),
            Skill(id=10, name="龙爪",       energy_consumption=3, category="物攻", attribute_id=4, power=80,  description="以锐利的龙爪撕裂对手"),
            Skill(id=11, name="冰冻光线",   energy_consumption=4, category="魔攻", attribute_id=5, power=90,  description="发射冰冻光线，可能令对手冰冻"),
            Skill(id=12, name="暴风雪",     energy_consumption=5, category="魔攻", attribute_id=5, power=110, description="召唤暴风雪袭击对手"),
            Skill(id=13, name="撞击",       energy_consumption=1, category="物攻", attribute_id=6, power=40,  description="以身体撞击对手"),
            Skill(id=14, name="蓄力",       energy_consumption=1, category="变化", attribute_id=6, power=None, description="蓄积力量，提升下次攻击威力"),
            Skill(id=15, name="龙之舞",     energy_consumption=2, category="变化", attribute_id=4, power=None, description="跳起龙之舞，提升攻击和速度"),
        ]
        session.add_all(skills)

        # --- 精灵 ---
        sprites = [
            Sprite(id=1, name="焰火龙"),
            Sprite(id=2, name="水灵龟"),
            Sprite(id=3, name="翠叶蝶"),
            Sprite(id=4, name="霜翼龙"),
            Sprite(id=5, name="烈焰兽"),
        ]
        session.add_all(sprites)

        # --- 精灵-属性关联 ---
        sprite_attrs = [
            SpriteAttribute(sprite_id=1, attribute_id=1),  # 焰火龙: 火
            SpriteAttribute(sprite_id=1, attribute_id=4),  # 焰火龙: 龙
            SpriteAttribute(sprite_id=2, attribute_id=2),  # 水灵龟: 水
            SpriteAttribute(sprite_id=3, attribute_id=3),  # 翠叶蝶: 草
            SpriteAttribute(sprite_id=4, attribute_id=5),  # 霜翼龙: 冰
            SpriteAttribute(sprite_id=4, attribute_id=4),  # 霜翼龙: 龙
            SpriteAttribute(sprite_id=5, attribute_id=1),  # 烈焰兽: 火
        ]
        session.add_all(sprite_attrs)

        # --- 精灵-技能关联 ---
        sprite_skills = [
            # 焰火龙: 烈焰冲击、火焰旋风、鬼火、龙之波动、龙爪、龙之舞
            SpriteSkill(sprite_id=1, skill_id=1),
            SpriteSkill(sprite_id=1, skill_id=2),
            SpriteSkill(sprite_id=1, skill_id=3),
            SpriteSkill(sprite_id=1, skill_id=9),
            SpriteSkill(sprite_id=1, skill_id=10),
            SpriteSkill(sprite_id=1, skill_id=15),
            # 水灵龟: 水炮、水流喷射、祈雨、撞击
            SpriteSkill(sprite_id=2, skill_id=4),
            SpriteSkill(sprite_id=2, skill_id=5),
            SpriteSkill(sprite_id=2, skill_id=6),
            SpriteSkill(sprite_id=2, skill_id=13),
            # 翠叶蝶: 日光束、叶刃、撞击、蓄力
            SpriteSkill(sprite_id=3, skill_id=7),
            SpriteSkill(sprite_id=3, skill_id=8),
            SpriteSkill(sprite_id=3, skill_id=13),
            SpriteSkill(sprite_id=3, skill_id=14),
            # 霜翼龙: 冰冻光线、暴风雪、龙之波动、龙爪、龙之舞
            SpriteSkill(sprite_id=4, skill_id=9),
            SpriteSkill(sprite_id=4, skill_id=10),
            SpriteSkill(sprite_id=4, skill_id=11),
            SpriteSkill(sprite_id=4, skill_id=12),
            SpriteSkill(sprite_id=4, skill_id=15),
            # 烈焰兽: 烈焰冲击、火焰旋风、鬼火、撞击、蓄力
            SpriteSkill(sprite_id=5, skill_id=1),
            SpriteSkill(sprite_id=5, skill_id=2),
            SpriteSkill(sprite_id=5, skill_id=3),
            SpriteSkill(sprite_id=5, skill_id=13),
            SpriteSkill(sprite_id=5, skill_id=14),
        ]
        session.add_all(sprite_skills)

        session.commit()
