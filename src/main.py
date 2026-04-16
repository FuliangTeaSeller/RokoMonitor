"""RokoMonitor 应用入口"""

import sys

from PyQt6.QtWidgets import QApplication

from src.database.connection import init_db, get_session
from src.ui.main_window import MainWindow


def main():
    # 初始化数据库（建表 + 种子数据）
    init_db()

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
