# -*- coding: utf-8 -*-
"""差旅搭子 - 程序入口。"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from db.database import get_db
from ui.main_window import MainWindow
from ui.theme import apply_theme
from ui.icons import icon as _icon
import config


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationDisplayName(config.APP_NAME)

    # 统一外观（设计系统：蓝青主题 + Fusion）
    apply_theme(app)
    app.setWindowIcon(_icon("plane", "#2563EB", 64))

    db = get_db()
    win = MainWindow(db)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
