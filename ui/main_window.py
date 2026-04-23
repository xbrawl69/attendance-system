import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QStackedWidget, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from ui.dashboard    import DashboardPage
from ui.add_student  import AddStudentPage
from ui.attendance_session import AttendancePage
from ui.reports      import ReportsPage
from ui.settings     import SettingsPage
from utils.config import APP_VERSION

NAV_STYLE = """
    QPushButton {
        background: transparent;
        color: #8B949E;
        border: none;
        padding: 14px 20px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
        border-radius: 8px;
    }
    QPushButton:hover   { background: #2C3035; color: #E0E6ED; }
    QPushButton:checked { background: rgba(0, 210, 255, 0.1); color: #00D2FF; font-weight: bold; border-left: 4px solid #00D2FF; }
"""

SIDEBAR_STYLE = "background-color: #111214; border-right: 1px solid #2C3035; min-width: 220px; max-width: 220px;"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Attendance System")
        self.setMinimumSize(1200, 750)
        self.setStyleSheet("background-color: #0D0E10; color: #E0E6ED;")
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setStyleSheet(SIDEBAR_STYLE)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 30, 16, 20)
        side_layout.setSpacing(8)

        logo = QLabel("Menu")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFont(QFont("Segoe UI", 18, QFont.Bold))
        logo.setStyleSheet("color: #FFFFFF; padding: 10px 0 22px 0;")
        side_layout.addWidget(logo)

        self.nav_buttons = []
        nav_items = [
            ("  Home",             0),
            ("  Add Student",      1),
            ("  Take Attendance",  2),
            ("  Reports",          3),
            ("  Settings",         4),
        ]
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(NAV_STYLE)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        side_layout.addStretch()

        version = QLabel(f"Attendance System {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #4C566A; font-size: 11px;")
        side_layout.addWidget(version)

        # ── Pages ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: transparent;")
        self.stack.addWidget(DashboardPage())
        self.stack.addWidget(AddStudentPage())
        self.stack.addWidget(AttendancePage())
        self.stack.addWidget(ReportsPage())
        self.stack.addWidget(SettingsPage())

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack)
        self.setCentralWidget(root)
        self._switch_page(0)

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
