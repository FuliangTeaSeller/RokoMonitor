"""SQLAlchemy ORM 模型定义"""

from sqlalchemy import Column, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Attribute(Base):
    __tablename__ = "attribute"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    image_path = Column(Text)

    skills = relationship("Skill", back_populates="attribute")
    sprites = relationship("SpriteAttribute", back_populates="attribute")


class Skill(Base):
    __tablename__ = "skill"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    energy_consumption = Column(Integer, nullable=False)
    category = Column(Text, nullable=False)
    attribute_id = Column(Integer, ForeignKey("attribute.id"), nullable=False)
    power = Column(Integer)
    description = Column(Text)
    beizhu = Column(Text)
    image_path = Column(Text)

    attribute = relationship("Attribute", back_populates="skills")
    sprites = relationship("SpriteSkill", back_populates="skill")

    __table_args__ = (
        CheckConstraint("category IN ('魔攻', '物攻', '变化')", name="ck_skill_category"),
    )


class Sprite(Base):
    __tablename__ = "sprite"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    image_path = Column(Text)

    attributes = relationship("SpriteAttribute", back_populates="sprite", cascade="all, delete-orphan")
    skills = relationship("SpriteSkill", back_populates="sprite", cascade="all, delete-orphan")


class SpriteAttribute(Base):
    __tablename__ = "sprite_attribute"

    sprite_id = Column(Integer, ForeignKey("sprite.id", ondelete="CASCADE"), primary_key=True)
    attribute_id = Column(Integer, ForeignKey("attribute.id", ondelete="CASCADE"), primary_key=True)

    sprite = relationship("Sprite", back_populates="attributes")
    attribute = relationship("Attribute", back_populates="sprites")


class SpriteSkill(Base):
    __tablename__ = "sprite_skill"

    sprite_id = Column(Integer, ForeignKey("sprite.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True)

    sprite = relationship("Sprite", back_populates="skills")
    skill = relationship("Skill", back_populates="sprites")
