# RokoMonitor

洛克王国世界 PVP 对战辅助工具 - 最小可行版本

## 快速启动

### Windows
双击 `run.bat` 或执行：
```bash
conda activate rokomonitor
python -m src.main
```

## 功能

1. **精灵搜索** - 搜索精灵并查看技能池
2. **悬浮窗** - 置顶显示对方精灵信息（可拖动、可关闭）
3. **手动录入** - 添加新的精灵和技能
4. **数据导入** - 从HTML技能图鉴导入数据

## 已实现模块

```
src/
├── config.py              # 全局配置
├── main.py               # 应用入口
├── database/
│   ├── models.py          # SQLAlchemy ORM 模型
│   ├── connection.py      # 数据库连接与种子数据
│   └── queries.py        # 查询接口
└── ui/
    ├── main_window.py     # 主窗口
    ├── overlay.py         # 悬浮窗
    └── entry_dialog.py   # 手动录入对话框
```

## Mock 数据

- 6 个属性：火、水、草、龙、冰、普通
- 5 只精灵：焰火龙、水灵龟、翠叶蝶、霜翼龙、烈焰兽
- 15 个技能

## 依赖

- PyQt6 >= 6.6
- SQLAlchemy >= 2.0
- Pillow >= 10.0
- beautifulsoup4 >= 4.12

## 工具脚本

`tools/` 目录下提供以下实用脚本：

### 数据导入

- **[tools/import_skills_from_html.py](tools/import_skills_from_html.py)** - 从技能图鉴HTML导入数据
  - 自动解析HTML提取技能信息
  - 转换webp图片为png格式
  - 自动创建属性和技能记录

- **[tools/clean_data.py](tools/clean_data.py)** - 清空数据库所有数据

### 批处理文件

- **[install_deps.bat](install_deps.bat)** - 安装项目依赖
- **[tools/run_import.bat](tools/run_import.bat)** - 运行技能导入脚本
- **[tools/setup_and_import.bat](tools/setup_and_import.bat)** - 一键安装依赖并导入数据

### 测试

- **[tools/test_dependencies.py](tools/test_dependencies.py)** - 测试依赖是否正确安装

### 使用方法

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
