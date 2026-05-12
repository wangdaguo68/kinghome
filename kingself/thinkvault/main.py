"""ThinkVault 入口。"""

import sys
import os

# 确保 thinkvault 包内部导入正常
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

import core.database as db
from ui.main_window import MainWindow


def main():
    db.init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("ThinkVault")
    app.setOrganizationName("ThinkVault")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
