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
