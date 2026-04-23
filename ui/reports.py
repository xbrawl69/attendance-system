import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
from core.attendance_logger import get_attendance_report
from utils.report_generator import export_csv, export_pdf

BTN_STYLE = """
    QPushButton {
        background: #2C3035; color: #E0E6ED; border: 1px solid #3A3F44;
        border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: bold;
    }
    QPushButton:hover { background: #3A3F44; }
"""

BTN_GREEN = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #98C379, stop:1 #7CB342);
        color: white; border: none;
        border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: bold;
    }
    QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7CB342, stop:1 #98C379); }
"""

class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #141619; color: #E0E6ED;")
        self._records = []
        self._build_ui()
        self._load_records()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel("Attendance Reports")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame { background: #1C1E22; border-radius: 12px; border: 1px solid #2C3035; }"
        )
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(20, 16, 20, 16)
        filter_layout.setSpacing(16)

        from_lbl = QLabel("From:")
        from_lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setStyleSheet(
            "QDateEdit { border: 1px solid #3A3F44; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #111214; color: #E0E6ED; }"
            "QDateEdit::drop-down { border: none; background: transparent; }"
        )

        to_lbl = QLabel("To:")
        to_lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setStyleSheet(
            "QDateEdit { border: 1px solid #3A3F44; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #111214; color: #E0E6ED; }"
            "QDateEdit::drop-down { border: none; background: transparent; }"
        )

        btn_filter = QPushButton("Apply Filter")
        btn_filter.setStyleSheet(BTN_STYLE)
        btn_filter.clicked.connect(self._load_records)

        btn_all = QPushButton("Show All")
        btn_all.setStyleSheet(BTN_STYLE)
        btn_all.clicked.connect(self._load_all)

        btn_csv = QPushButton("Export CSV")
        btn_csv.setStyleSheet(BTN_GREEN)
        btn_csv.clicked.connect(self._export_csv)

        btn_pdf = QPushButton("Export PDF")
        btn_pdf.setStyleSheet(BTN_GREEN)
        btn_pdf.clicked.connect(self._export_pdf)

        for w in (from_lbl, self.date_from, to_lbl, self.date_to, btn_filter, btn_all):
            filter_layout.addWidget(w)
        filter_layout.addStretch()
        for w in (btn_csv, btn_pdf):
            filter_layout.addWidget(w)
        layout.addWidget(filter_frame)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Student ID", "Name", "Roll No", "Department",
            "Date", "Session", "Time"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #111214; border-radius: 12px;
                border: 1px solid #2C3035; color: #E0E6ED;
                font-size: 13px; outline: none;
            }
            QTableWidget::item { padding: 12px; border-bottom: 1px solid #2C3035; }
            QHeaderView::section {
                background: #1C1E22; color: #8B949E;
                padding: 12px; font-size: 12px; font-weight: bold;
                border: none; border-bottom: 2px solid #2C3035; text-transform: uppercase;
            }
            QTableWidget::item:alternate { background: #181A1F; }
            QTableWidget::item:selected { background: rgba(0, 210, 255, 0.15); color: #FFFFFF; }
        """)
        layout.addWidget(self.table)

        self.lbl_count = QLabel("0 records")
        self.lbl_count.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.lbl_count)

    def _load_records(self):
        from_date = self.date_from.date().toString("yyyy-MM-dd")
        to_date   = self.date_to.date().toString("yyyy-MM-dd")
        self._records = get_attendance_report(from_date, to_date)
        self._populate_table()

    def _load_all(self):
        self._records = get_attendance_report()
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        keys = ["student_id", "name", "roll_number", "department", "date", "session_name", "timestamp"]
        for rec in self._records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(keys):
                item = QTableWidgetItem(str(rec.get(key, "")))
                self.table.setItem(row, col, item)
        self.lbl_count.setText(f"{len(self._records)} records found")

    def _export_csv(self):
        if not self._records:
            QMessageBox.information(self, "No Data", "No records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "attendance_report.csv", "CSV Files (*.csv)")
        if path:
            export_csv(self._records, path)
            QMessageBox.information(self, "Done", f"✓ CSV saved to:\n{path}")

    def _export_pdf(self):
        if not self._records:
            QMessageBox.information(self, "No Data", "No records to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "attendance_report.pdf", "PDF Files (*.pdf)")
        if path:
            export_pdf(self._records, path, "Attendance Report")
            QMessageBox.information(self, "Done", f"✓ PDF saved to:\n{path}")
