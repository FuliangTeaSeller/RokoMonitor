# RokoMonitor 数据库工具

本目录包含 RokoMonitor 项目的数据库初始化脚本。

## 数据库初始化脚本

### `init_database.sql`

用于初始化 SQLite 数据库，创建以下表结构：

- **attribute** - 属性表（龙/火/水/草/冰等）
- **skill** - 技能表
- **sprite** - 精灵表
- **sprite_attribute** - 精灵-属性关联表（多对多）
- **sprite_skill** - 精灵-技能关联表（多对多）

以及必要的索引以优化查询性能。

## 使用方法

### 使用命令行初始化

```bash
# 在项目根目录下执行
sqlite3 roko_monitor.db < tools/init_database.sql
```

### 使用 Python 脚本初始化

```python
import sqlite3

# 连接数据库（不存在则创建）
conn = sqlite3.connect('roko_monitor.db')
cursor = conn.cursor()

# 读取并执行初始化脚本
with open('tools/init_database.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()
    cursor.executescript(sql_script)

# 提交更改
conn.commit()
conn.close()
```

### 使用 SQLite GUI 工具

可以使用 DB Browser for SQLite、DBeaver 等 GUI 工具打开 `init_database.sql` 文件并执行。

## 数据库表关系

```
attribute ──1:N── sprite_attribute ──N:1── sprite ──M:N── sprite_skill ──N:1── skill
     │                                              │                      │
     └── attribute_image (1:1)                  sprite_image (1:1)     skill_image (1:1)
```

## 注意事项

1. 脚本会先删除现有表（如果存在），谨慎在生产环境使用
2. 属性表需最先创建，被其他表引用
3. 所有外键关系都设置了 `ON DELETE CASCADE`，删除主记录会自动删除关联记录
4. 图片路径约定：`data/images/{type}/{id}.png`
