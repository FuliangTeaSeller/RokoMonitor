-- RokoMonitor SQLite 数据库初始化脚本
-- 用于创建 RokoMonitor 所需的所有表结构和索引

-- 清理现有表（按依赖关系倒序删除）
DROP TABLE IF EXISTS sprite_skill;
DROP TABLE IF EXISTS sprite_attribute;
DROP TABLE IF EXISTS sprite;
DROP TABLE IF EXISTS skill;
DROP TABLE IF EXISTS attribute;

-- ============================================
-- 1. 属性表（需最先创建，被技能表和精灵-属性关联表引用）
-- ============================================
CREATE TABLE attribute (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    image_path  TEXT
);

-- ============================================
-- 2. 技能表
-- ============================================
CREATE TABLE skill (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    energy_consumption INTEGER NOT NULL,
    category    TEXT    NOT NULL CHECK (category IN ('魔攻', '物攻', '变化')),
    attribute_id INTEGER NOT NULL,
    power       INTEGER,
    description TEXT,
    beizhu      TEXT,
    image_path  TEXT,
    FOREIGN KEY (attribute_id) REFERENCES attribute(id)
);

-- ============================================
-- 3. 精灵表
-- ============================================
CREATE TABLE sprite (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    image_path  TEXT
);

-- ============================================
-- 4. 精灵-属性关联表（支持多属性）
-- ============================================
CREATE TABLE sprite_attribute (
    sprite_id    INTEGER NOT NULL,
    attribute_id INTEGER NOT NULL,
    PRIMARY KEY (sprite_id, attribute_id),
    FOREIGN KEY (sprite_id)    REFERENCES sprite(id)    ON DELETE CASCADE,
    FOREIGN KEY (attribute_id) REFERENCES attribute(id) ON DELETE CASCADE
);

-- ============================================
-- 5. 精灵-技能关联表
-- ============================================
CREATE TABLE sprite_skill (
    sprite_id INTEGER NOT NULL,
    skill_id  INTEGER NOT NULL,
    PRIMARY KEY (sprite_id, skill_id),
    FOREIGN KEY (sprite_id) REFERENCES sprite(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)  REFERENCES skill(id)  ON DELETE CASCADE
);

-- ============================================
-- 6. 创建索引
-- ============================================

-- 精灵名称查询（对战识别主路径）
CREATE INDEX idx_sprite_name ON sprite(name);

-- 技能名称查询
CREATE INDEX idx_skill_name ON skill(name);

-- 按精灵查技能池
CREATE INDEX idx_sprite_skill_sprite ON sprite_skill(sprite_id);

-- 按技能反查精灵
CREATE INDEX idx_sprite_skill_skill ON sprite_skill(skill_id);

-- 按精灵查属性
CREATE INDEX idx_sprite_attribute_sprite ON sprite_attribute(sprite_id);

-- 属性名称查询
CREATE INDEX idx_attribute_name ON attribute(name);

-- ============================================
-- 初始化完成
-- ============================================
