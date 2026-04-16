"""RokoMonitor 应用入口"""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from src.database.connection import init_db, get_session
from src.ui.main_window import MainWindow


def setup_logging():
    """配置日志"""
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 配置第三方库的日志级别
    logging.getLogger("paddleocr").setLevel(logging.WARNING)
    logging.getLogger("Paddle").setLevel(logging.WARNING)


def main():
    # 配置日志
    setup_logging()
    logging.info("RokoMonitor 启动")

    # 初始化数据库（建表 + 种子数据）
    init_db()
    logging.info("数据库初始化完成")

    # 启动 Qt 应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    session = get_session()
    window = MainWindow(session)
    window.show()

    exit_code = app.exec()
    session.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
