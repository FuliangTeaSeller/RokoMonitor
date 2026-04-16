# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 注意事项
- 编写代码前，查看/docs/文件夹下的内容
- 用户偏好中文
- 代码完成后，回顾/docs/文件夹内容是否需要更改

# 运行环境
## Python 环境
- 激活 conda 环境: `conda activate rokomonitor`
- 项目使用 Python 3.11+

## 常用命令

### 启动应用
```bash
# 手动启动
conda activate rokomonitor
python -m src.main
```

### 依赖管理
```bash
# 安装依赖
conda activate rokomonitor
pip install -r requirements.txt

# 测试依赖是否正确安装
python tools/test_dependencies.py
```

### 数据导入
```bash
# 一键安装依赖并导入技能数据
tools\setup_and_import.bat

# 单独运行技能导入
python tools/import_skills_from_html.py

# 单独运行精灵导入
python tools/import_sprites_from_html.py

# 精灵-技能绑定批量导入（从JSON文件）
python tools/import_sprite_skills.py reference/sprite_skills_example.json

# 清空数据库
python tools/clean_data.py
```

# 项目架构

## 核心模块结构

```
src/
├── main.py                 # 应用入口，初始化数据库并启动主窗口
├── config.py              # 全局配置（数据库路径等）
├── database/
│   ├── models.py          # SQLAlchemy ORM 模型（Attribute, Skill, Sprite, SpriteAttribute, SpriteSkill）
│   ├── connection.py      # 数据库连接、建表、种子数据
│   └── queries.py         # 查询接口（search_sprites_by_name, get_sprite_detail, add_sprite, add_skill）
└── ui/
    ├── main_window.py     # 主窗口（搜索精灵、显示技能池、打开悬浮窗/录入）
    ├── overlay.py         # 悬浮窗（置顶显示精灵信息）
    ├── entry_dialog.py    # 手动录入对话框
    └── image_utils.py     # 图片加载工具
```

## 数据库架构

### 表关系
```
attribute ──1:N── sprite_attribute ──N:1── sprite ──M:N── sprite_skill ──N:1── skill
```

### 关键模型
- **Attribute**: 属性表（火、水、草、龙、冰等），每个技能有单一属性，精灵可有多个属性
- **Skill**: 技能表，包含技能名称、能耗、类别（魔攻/物攻/变化）、威力、描述、图片路径
- **Sprite**: 精灵表，包含精灵名称、图片路径
- **SpriteAttribute**: 精灵-属性多对多关联表
- **SpriteSkill**: 精灵-技能多对多关联表

### 数据库初始化
- 数据库文件: `roko_monitor.db` (项目根目录)
- 建表和种子数据在 `connection.py` 的 `init_db()` 中自动执行
- 种子数据包含 6 个属性、5 只精灵、15 个技能

## 数据查询接口 (queries.py)

主要查询函数：
- `search_sprites_by_name(session, keyword)` - 模糊搜索精灵
- `get_sprite_detail(session, sprite_id)` - 获取精灵完整详情（属性+技能池）
- `get_sprite_detail_by_name(session, name)` - 按名称精确查询
- `add_sprite(session, name, attribute_ids, skill_ids)` - 新增精灵
- `add_skill(session, name, attribute_id, category, energy_consumption, power, description)` - 新增技能

## UI 模块

### MainWindow (main_window.py)
主窗口功能：
- 搜索栏：输入精灵名称搜索
- 搜索结果列表：显示匹配的精灵（含图标）
- 技能池详情：表格展示精灵技能（图标、名称、属性、类别、威力、能耗、描述）
- 悬浮窗查看按钮：打开置顶悬浮窗
- 手动录入按钮：打开数据录入对话框

### OverlayWindow (overlay.py)
悬浮窗特性：
- 置顶显示（WindowStaysOnTopHint）
- 无边框窗口（FramelessWindowHint）
- 可拖动
- 固定尺寸 380x420
- 显示精灵图标、名称、属性、技能表格
- 点击技能显示描述

## 数据导入工具

### HTML 数据源
- 技能数据: `reference/技能/技能图鉴.html`
- 精灵数据: `reference/精灵/精灵图鉴 _ 洛克王国_ 世界.html`

### 导入脚本功能
- `import_skills_from_html.py`: 从技能图鉴HTML导入技能数据
  - 解析HTML提取技能信息
  - 转换webp图片为png格式
  - 自动创建属性记录
  - 跳过已存在的技能

- `import_sprites_from_html.py`: 从精灵图鉴HTML导入精灵数据
  - 解析HTML提取精灵名称、属性、图片
  - 复制精灵图片到 `data/images/sprites/`
  - 创建属性记录并关联

- `import_sprite_skills.py`: 从JSON文件批量导入精灵-技能绑定
  - JSON格式使用精灵名称和技能名称，便于编辑
  - 支持增量导入，不删除已有技能
  - 幂等性：已存在的绑定自动跳过
  - 示例文件: `reference/sprite_skills_example.json`

## 图片存储约定

```
data/images/
├── attributes/       # 属性图标，文件名 = 属性英文名
│   ├── fire.png
│   ├── water.png
│   └── ...
├── sprites/          # 精灵图片，文件名 = 精灵id
│   ├── 1.png
│   └── ...
└── skills/           # 技能图标，文件名 = 技能id
    ├── 1.png
    └── ...
```

## 数据类 (queries.py)

- `SkillInfo`: 技能简要信息（id, name, attribute, category, power, energy_consumption, description, image_path）
- `SpriteInfo`: 精灵完整信息（id, name, image_path, attributes, skills）

# 技术栈
- **UI框架**: PyQt6 >= 6.6
- **数据库**: SQLite + SQLAlchemy >= 2.0
- **图片处理**: Pillow >= 10.0
- **HTML解析**: beautifulsoup4 >= 4.12
- **设计风格**: Catppuccin Mocha 深色主题
