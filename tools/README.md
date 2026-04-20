# RokoMonitor 数据库工具

本目录包含 RokoMonitor 项目的数据库初始化脚本和数据导入工具。

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
sqlite3 data/roko_monitor.db < tools/init_database.sql
```

### 使用 Python 脚本初始化

```python
import sqlite3

# 连接数据库（不存在则创建）
conn = sqlite3.connect('data/roko_monitor.db')
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

---

## 数据导入工具

### `import_skills_from_html.py`

从技能图鉴HTML文件中提取技能数据并导入到数据库。

**功能：**
- 解析HTML提取技能名称、耗能、分类、属性、威力、描述
- 自动映射分类（状态/防御 → 变化）
- 将webp图片转换为png格式
- 自动创建属性记录
- 跳过已存在的技能

**用法：**
```cmd
python tools/import_skills_from_html.py
```

**依赖：**
- Pillow (图片处理)
- beautifulsoup4 (HTML解析)

### `clean_data.py`

清空数据库所有数据。

**用法：**
```cmd
python tools/clean_data.py
```

**注意：** 此操作会删除所有数据，请谨慎使用！

### `test_dependencies.py`

测试所有依赖包是否正确安装。

**用法：**
```cmd
python tools/test_dependencies.py
```

---

## 批处理文件

### `run_import.bat`

运行技能导入脚本（需要先激活conda环境）。

### `setup_and_import.bat`

一键安装依赖并导入技能数据：
1. 安装requirements.txt中的所有依赖
2. 测试依赖是否安装成功
3. 运行技能导入脚本

---

## 快速开始

**方式一：一键安装并导入**
```cmd
双击 tools\setup_and_import.bat
```

**方式二：手动执行**
```cmd
conda activate rokomonitor
pip install -r requirements.txt
python tools/import_skills_from_html.py
```

---

## 文件路径配置

脚本中使用的路径：
- HTML文件: `reference/技能/技能图鉴.html`
- HTML资源文件: `reference/技能/技能图鉴_files/`
- 数据库: `data/roko_monitor.db`
- 技能图片: `data/images/skills/`
- 属性图片: `data/images/attributes/`
