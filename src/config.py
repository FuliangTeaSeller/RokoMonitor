"""全局配置"""

from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 数据库文件路径
DATABASE_PATH = PROJECT_ROOT / "roko_monitor.db"
