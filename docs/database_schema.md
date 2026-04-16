# RokoMonitor 数据库表结构设计

## 1. ER 关系

```
attribute ──1:N── sprite_attribute ──N:1── sprite ──M:N── sprite_skill ──N:1── skill
     │                                              │                      │
     └── attribute_image (1:1)                  sprite_image (1:1)     skill_image (1:1)
```

- 精灵与技能为多对多关系（一只精灵可学多个技能，一个技能可被多只精灵学习）
- 精灵可拥有多个属性，通过 `sprite_attribute` 关联表实现多对多
- 技能的 `attribute_id` 为单一属性（一个技能只有一个属性）
- 属性、精灵、技能各有独立图片，图片以本地文件路径存储

## 2. 表结构

### 2.1 attribute（属性表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY | 属性 ID |
| name | TEXT | NOT NULL UNIQUE | 属性名称（龙/火/水/草/冰等） |
| image_path | TEXT | | 属性图标本地路径（如 `data/images/attributes/fire.png`） |

```sql
CREATE TABLE attribute (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    image_path  TEXT
);
```

### 2.2 skill（技能表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY | 技能 ID |
| name | TEXT | NOT NULL UNIQUE | 技能名称 |
| energy_consumption | INTEGER | NOT NULL | 能量消耗 |
| category | TEXT | NOT NULL | 类别（魔攻/物攻/变化） |
| attribute_id | INTEGER | NOT NULL FOREIGN KEY → attribute.id | 技能属性（单属性） |
| power | INTEGER | | 威力（变化类技能为 NULL） |
| description | TEXT | | 技能描述 |
| beizhu | TEXT | | 备注 |
| image_path | TEXT | | 技能图标本地路径（如 `data/images/skills/6.png`） |

```sql
CREATE TABLE skill (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    energy_consumption INTEGER NOT NULL,
    category    TEXT    NOT NULL CHECK (category IN ('魔攻', '物攻', '变化')),
    attribute_id INTEGER NOT NULL,
    power       INTEGER,
    description TEXT,
    beizhu      TEXT,
    image_path  TEXT,
    FOREIGN KEY (attribute_id) REFERENCES attribute(id)
);
```

### 2.3 sprite（精灵表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY | 精灵 ID |
| name | TEXT | NOT NULL UNIQUE | 精灵名称 |
| image_path | TEXT | | 精灵图片本地路径（如 `data/images/sprites/1.png`） |

```sql
CREATE TABLE sprite (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    image_path  TEXT
);
```

### 2.4 sprite_attribute（精灵-属性关联表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| sprite_id | INTEGER | FOREIGN KEY → sprite.id | 精灵 ID |
| attribute_id | INTEGER | FOREIGN KEY → attribute.id | 属性 ID |

```sql
CREATE TABLE sprite_attribute (
    sprite_id    INTEGER NOT NULL,
    attribute_id INTEGER NOT NULL,
    PRIMARY KEY (sprite_id, attribute_id),
    FOREIGN KEY (sprite_id)    REFERENCES sprite(id)    ON DELETE CASCADE,
    FOREIGN KEY (attribute_id) REFERENCES attribute(id) ON DELETE CASCADE
);
```

### 2.5 sprite_skill（精灵-技能关联表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| sprite_id | INTEGER | FOREIGN KEY → sprite.id | 精灵 ID |
| skill_id | INTEGER | FOREIGN KEY → skill.id | 技能 ID |

```sql
CREATE TABLE sprite_skill (
    sprite_id INTEGER NOT NULL,
    skill_id  INTEGER NOT NULL,
    PRIMARY KEY (sprite_id, skill_id),
    FOREIGN KEY (sprite_id) REFERENCES sprite(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)  REFERENCES skill(id)  ON DELETE CASCADE
);
```

## 3. 索引

```sql
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
```

## 4. 图片存储约定

```
data/images/
├── attributes/       # 属性图标，文件名 = 属性英文名
│   ├── fire.png
│   ├── water.png
│   ├── dragon.png
│   └── ...
├── sprites/          # 精灵图片，文件名 = 精灵id
│   ├── 1.png
│   ├── 2.png
│   └── ...
└── skills/           # 技能图标，文件名 = 技能id
    ├── 1.png
    ├── 6.png
    └── ...
```

- 图片路径以 `data/images/` 为根的相对路径存入数据库
- 统一使用 PNG 格式
- 数据库中 `image_path` 字段存储示例：`data/images/sprites/1.png`

## 5. 建库脚本（完整）

```sql
-- RokoMonitor SQLite 建库脚本

-- 属性表（需最先创建，被技能表和精灵-属性关联表引用）
CREATE TABLE attribute (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    image_path  TEXT
);

-- 技能表
CREATE TABLE skill (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    energy_consumption INTEGER NOT NULL,
    category    TEXT    NOT NULL CHECK (category IN ('魔攻', '物攻', '变化')),
    attribute_id INTEGER NOT NULL,
    power       INTEGER,
    description TEXT,
    beizhu      TEXT,
    image_path  TEXT,
    FOREIGN KEY (attribute_id) REFERENCES attribute(id)
);

-- 精灵表
CREATE TABLE sprite (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    image_path  TEXT
);

-- 精灵-属性关联表（支持多属性）
CREATE TABLE sprite_attribute (
    sprite_id    INTEGER NOT NULL,
    attribute_id INTEGER NOT NULL,
    PRIMARY KEY (sprite_id, attribute_id),
    FOREIGN KEY (sprite_id)    REFERENCES sprite(id)    ON DELETE CASCADE,
    FOREIGN KEY (attribute_id) REFERENCES attribute(id) ON DELETE CASCADE
);

-- 精灵-技能关联表
CREATE TABLE sprite_skill (
    sprite_id INTEGER NOT NULL,
    skill_id  INTEGER NOT NULL,
    PRIMARY KEY (sprite_id, skill_id),
    FOREIGN KEY (sprite_id) REFERENCES sprite(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)  REFERENCES skill(id)  ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_sprite_name ON sprite(name);
CREATE INDEX idx_skill_name ON skill(name);
CREATE INDEX idx_sprite_skill_sprite ON sprite_skill(sprite_id);
CREATE INDEX idx_sprite_skill_skill ON sprite_skill(skill_id);
CREATE INDEX idx_sprite_attribute_sprite ON sprite_attribute(sprite_id);
CREATE INDEX idx_attribute_name ON attribute(name);
```
