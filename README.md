# RokoMonitor

<img src="reference/图片/logo.png" alt="Logo" width="120" height="120">

洛克王国世界 PVP 对战辅助工具

## 如何使用

### 首次使用（创建环境）
```bash
conda create -n rokomonitor python=3.11
```

### 安装依赖
双击运行 `install.bat`

或手动执行：
```bash
conda activate rokomonitor
pip install -r requirements.txt
```

### 运行
双击运行 `run.bat`

或手动执行：
```bash
conda activate rokomonitor
python -m src.main
```

## 功能

1. **精灵搜索** - 搜索精灵并查看技能池
2. **悬浮窗** - 置顶显示对方精灵信息（可拖动、可关闭）
3. **手动录入** - 添加新的精灵和技能
4. **配队识别** - OCR 自动识别对方阵容精灵及技能
5. **数据导入** - 从HTML技能图鉴导入数据

## 项目结构

```
src/
├── config.py              # 全局配置（截图区域、OCR参数）
├── main.py               # 应用入口
├── database/
│   ├── models.py          # SQLAlchemy ORM 模型
│   ├── connection.py      # 数据库连接与种子数据
│   └── queries.py        # 查询接口
├── capture/
│   └── screen_capture.py  # 屏幕截图（基于 mss）
├── ocr/
│   ├── engine.py          # OCR 引擎（基于 PaddleOCR）
│   └── text_match.py      # 精灵名称模糊匹配
├── utils/
│   └── pinyin_service.py  # 拼音服务
└── ui/
    ├── main_window.py     # 主窗口
    ├── overlay.py         # 悬浮窗
    ├── entry_dialog.py    # 手动录入对话框
    └── team_dialog.py     # 配队识别对话框
```

## 依赖

- PyQt6 >= 6.6
- SQLAlchemy >= 2.0
- Pillow >= 10.0
- beautifulsoup4 >= 4.12
- mss >= 9.0（屏幕截图）
- paddleocr >= 3.2（OCR 识别）
- thefuzz >= 0.22（模糊匹配）
- numpy >= 1.24

## 配队识别功能

配队识别功能可以自动识别游戏中的精灵阵容：

### 识别模式
- **单次识别** - 手动触发一次识别
- **自动识别** - 按设定间隔持续识别

### 截图区域
- **右上角（单精灵）** - 识别屏幕右上角的单个精灵
- **配队列表（全阵容）** - 识别对方阵容列表
- **首发页面（6精灵）** - 识别首发选择页面

### 功能特性
- 6 个精灵槽位，支持识别覆盖和手动输入
- 横向滚动查看技能详情
- 全屏展示模式
- 截图预览
- 识别成功率统计

