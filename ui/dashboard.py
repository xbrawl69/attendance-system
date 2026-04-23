import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
from database.db_handler import get_connection

CARD_STYLE = """
    QFrame {
        background: #1C1E22;
        border-radius: 12px;
        border: 1px solid #2C3035;
    }
"""

class StatButton(QPushButton):
    def __init__(self, title, value, color):
        super().__init__()
        self.setStyleSheet(f"""
            QPushButton {{
                background: #1C1E22;
                border-radius: 14px;
                border: 1px solid #2C3035;
                border-top: 3px solid {color};
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{ background: #20242A; border-color: {color}; }}
            QPushButton:checked {{ background: #232833; border: 1px solid {color}; border-top: 3px solid {color}; }}
        """)
        self.setCheckable(True)
        self.setMinimumHeight(100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents)
        lbl_title.setStyleSheet("color: #8B949E; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lbl_value.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.lbl_value.setStyleSheet(f"color: {color}; border: none; background: transparent;")

        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_value)

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #141619;")
        self._build_ui()
        self._refresh()
        timer = QTimer(self)
        timer.timeout.connect(self._refresh)
        timer.start(10000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        # Header
        self.lbl_date = QLabel()
        self.lbl_date.setStyleSheet("color: #00D2FF; font-size: 14px; font-weight: bold; border: none; background: transparent;")
        title = QLabel("System Home Overview")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; border: none;")
        
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        header_layout.addWidget(title)
        header_layout.addWidget(self.lbl_date)
        layout.addLayout(header_layout)

        # Stat cards row (Clickable)
        row = QHBoxLayout()
        row.setSpacing(20)
        
        self.btn_today = StatButton("Present Today", "0", "#00D2FF")
        self.btn_students = StatButton("Total Enrolled", "0", "#98C379")
        self.btn_sessions = StatButton("Active Sessions", "0", "#C678DD")
        
        self.btn_today.clicked.connect(lambda: self._switch_view(0))
        self.btn_students.clicked.connect(lambda: self._switch_view(1))
        self.btn_sessions.clicked.connect(lambda: self._switch_view(0)) # defaulting to recent
        
        self.btn_today.setChecked(True)

        for btn in (self.btn_today, self.btn_students, self.btn_sessions):
            row.addWidget(btn)
        layout.addLayout(row)

        # Dynamic Content Area (Stacked Widget)
        self.content_stack = QStackedWidget()
        
        ## View 0: Recent Attendance Activity
        self.recent_frame = QFrame()
        self.recent_frame.setStyleSheet(CARD_STYLE)
        rf_layout = QVBoxLayout(self.recent_frame)
        rf_layout.setContentsMargins(24, 20, 24, 20)
        rf_title = QLabel("Recent Attendance Activity")
        rf_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        rf_title.setStyleSheet("color: #FFFFFF; border: none;")
        rf_layout.addWidget(rf_title)
        self.recent_list = QVBoxLayout()
        self.recent_list.setSpacing(8)
        rf_layout.addLayout(self.recent_list)
        rf_layout.addStretch()
        
        ## View 1: Listed Enrolled Students
        self.students_frame = QFrame()
        self.students_frame.setStyleSheet(CARD_STYLE)
        st_layout = QVBoxLayout(self.students_frame)
        st_layout.setContentsMargins(24, 20, 24, 20)
        st_title = QLabel("Registered Students Directory")
        st_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        st_title.setStyleSheet("color: #FFFFFF; border: none;")
        st_layout.addWidget(st_title)
        
        self.student_table = QTableWidget()
        self.student_table.setColumnCount(6)
        self.student_table.setHorizontalHeaderLabels(["ID", "Name", "Roll No", "Department", "Course", "Semester"])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.student_table.verticalHeader().setVisible(False)
        self.student_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.student_table.setShowGrid(False)
        self.student_table.setStyleSheet("""
            QTableWidget {
                background: #1C1E22; border: none; color: #E0E6ED; font-size: 13px;
            }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #2C3035; }
            QHeaderView::section {
                background: #111214; color: #8B949E;
                padding: 10px; font-size: 12px; font-weight: bold; border: none; border-bottom: 2px solid #2C3035;
            }
        """)
        st_layout.addWidget(self.student_table)

        self.content_stack.addWidget(self.recent_frame)
        self.content_stack.addWidget(self.students_frame)
        
        layout.addWidget(self.content_stack)
        layout.addStretch()

    def _switch_view(self, index):
        self.btn_today.setChecked(index == 0)
        self.btn_sessions.setChecked(index == 0)
        self.btn_students.setChecked(index == 1)
        self.content_stack.setCurrentIndex(index)
        
    def _refresh(self):
        self.lbl_date.setText(datetime.now().strftime("%A, %d %B %Y  |  %I:%M %p"))
        try:
            with get_connection() as conn:
                from datetime import date
                today = date.today().isoformat()

                today_count = conn.execute(
                    "SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date=?", (today,)
                ).fetchone()[0]

                total_students = conn.execute(
                    "SELECT COUNT(*) FROM students"
                ).fetchone()[0]

                sessions = conn.execute(
                    "SELECT COUNT(DISTINCT session_name) FROM attendance WHERE date=?", (today,)
                ).fetchone()[0]

                recent_logs = conn.execute(
                    """SELECT s.name, a.timestamp, a.session_name
                       FROM attendance a
                       JOIN students s ON a.student_id = s.student_id
                       WHERE a.date = ?
                       ORDER BY a.timestamp DESC LIMIT 8""", (today,)
                ).fetchall()
                
                students_data = conn.execute(
                    """
                    SELECT student_id, name, roll_number, department, course, semester
                    FROM students
                    ORDER BY created_at DESC
                    """
                ).fetchall()

            self.btn_today.lbl_value.setText(str(today_count))
            self.btn_students.lbl_value.setText(str(total_students))
            self.btn_sessions.lbl_value.setText(str(sessions))

            while self.recent_list.count():
                item = self.recent_list.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if not recent_logs:
                lbl = QLabel("No attendance recorded today.")
                lbl.setStyleSheet("color: #5C6370; font-size: 13px; border: none; font-style: italic;")
                self.recent_list.addWidget(lbl)
            else:
                for row in recent_logs:
                    time_str = str(row[1]).split()[1] if ' ' in str(row[1]) else str(row[1])
                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(12, 10, 12, 10)
                    
                    name_lbl = QLabel(f"• {row[0]}")
                    name_lbl.setStyleSheet("color: #E0E6ED; font-size: 14px; font-weight: bold; border: none;")
                    
                    session_lbl = QLabel(row[2])
                    session_lbl.setStyleSheet("color: #E5C07B; font-size: 12px; font-weight: bold; border: none; background: #282C34; padding: 4px 8px; border-radius: 4px;")
                    
                    time_lbl = QLabel(time_str)
                    time_lbl.setStyleSheet("color: #8B949E; font-size: 13px; border: none;")
                    
                    row_layout.addWidget(name_lbl)
                    row_layout.addStretch()
                    row_layout.addWidget(session_lbl)
                    row_layout.addWidget(time_lbl)
                    
                    row_widget.setStyleSheet("background: #21252B; border-radius: 8px;")
                    self.recent_list.addWidget(row_widget)
                    
            # Populate Student Table
            self.student_table.setRowCount(0)
            for rec in students_data:
                row_idx = self.student_table.rowCount()
                self.student_table.insertRow(row_idx)
                for col_idx, val in enumerate(rec):
                    item = QTableWidgetItem(str(val))
                    item.setForeground(QColor("#E0E6ED"))
                    self.student_table.setItem(row_idx, col_idx, item)

        except Exception as e:
            print(f"[Dashboard] refresh error: {e}")
