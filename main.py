# -*- coding: utf-8 -*-
"""差旅搭子 - 程序入口。"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from db.database import get_db
from ui.main_window import MainWindow
import config


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationDisplayName(config.APP_NAME)

    # 统一外观
    app.setStyle("Fusion")
    font = QFont("Microsoft YaHei, PingFang SC, Noto Sans CJK SC, WenQuanYi Micro Hei, sans-serif", 10)
    app.setFont(font)

    db = get_db()
    win = MainWindow(db)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
