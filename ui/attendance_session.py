import os
import sys
import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QApplication, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QImage, QPixmap
from core.attendance_logger import log_attendance
from database.db_handler import get_connection

BTN_START = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00D2FF, stop:1 #3A7BD5);
        color: white; border: none;
        border-radius: 8px; padding: 12px 24px;
        font-size: 14px; font-weight: bold;
    }
    QPushButton:hover    { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3A7BD5, stop:1 #00D2FF); }
    QPushButton:disabled { background: #3A3F44; color: #7F8C8D; }
"""

BTN_STOP = """
    QPushButton {
        background: #E06C75; color: white; border: none;
        border-radius: 8px; padding: 12px 24px;
        font-size: 14px; font-weight: bold;
    }
    QPushButton:hover { background: #BE5046; }
    QPushButton:disabled { background: #3A3F44; color: #7F8C8D; }
"""

FIELD_STYLE = """
    QLineEdit, QComboBox {
        border: 1px solid #3A3F44;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        background: #1E2124;
        color: #E0E6ED;
    }
    QLineEdit:focus, QComboBox:focus { border: 1px solid #00D2FF; }
"""

class FaceRecognitionThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    student_identified_signal = pyqtSignal(str, str)
    
    def __init__(self, student_ids, encodings, student_names):
        super().__init__()
        self._run_flag = True
        self.student_ids = student_ids
        self.encodings = encodings
        self.student_names = student_names
        self.identity_history = {}
        
    def run(self):
        import cv2
        import numpy as np
        from utils.config import CAMERA_INDEX
        from core.face_recognition_engine import detect_faces, identify_face_dlib
        
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(CAMERA_INDEX)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
        identified_session_set = set()

        while self._run_flag:
            ret, frame = cap.read()
            if not ret: continue
            
            display_frame = frame.copy()
            faces = detect_faces(frame)
            
            for (x, y, w, h) in faces:
                pad_y = max(6, int(h * 0.12))
                pad_x = max(6, int(w * 0.12))
                y1, y2 = max(0, y-pad_y), min(frame.shape[0], y+h+pad_y)
                x1, x2 = max(0, x-pad_x), min(frame.shape[1], x+w+pad_x)
                face_crop_rgb = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)
                
                name, conf = identify_face_dlib(face_crop_rgb, self.student_ids, self.encodings)
                history_key = (x // 40, y // 40)
                history_buffer = self.identity_history.setdefault(history_key, [])
                history_buffer.append(name)
                if len(history_buffer) > 8:
                    history_buffer.pop(0)

                import collections
                stable_name = "Unknown" if name == "Unknown" else collections.Counter(history_buffer).most_common(1)[0][0]
                display_name = self.student_names.get(stable_name, stable_name)
                
                is_known = stable_name != "Unknown"
                color = (0, 0, 255) if is_known else (117, 108, 224)
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
                
                label = display_name if is_known else "Unknown"
                (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)
                
                cv2.rectangle(display_frame, (x, y + h), (x + max(text_width+10, w), y + h + text_height + 10), color, -1)
                cv2.putText(display_frame, label, (x + 5, y + h + text_height + 5), 
                            cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

                if is_known and stable_name not in identified_session_set:
                    identified_session_set.add(stable_name)
                    self.student_identified_signal.emit(stable_name, display_name)
                    
            rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.change_pixmap_signal.emit(qt_img)
            
        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class AttendancePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #141619; color: #E0E6ED;")
        self.thread = None
        self._staged_students = []
        self._current_session_full_name = ""
        self._pending_export_count = 0
        self._save_queue = []
        self._save_total = 0
        self._save_started_at = None
        self._last_session_saved_count = 0
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        # ── LEFT PANEL (Controls & Logs) ──
        left_widget = QWidget()
        left_widget.setFixedWidth(350)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        title = QLabel("Take Attendance")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        left_layout.addWidget(title)

        # Settings Card
        card = QFrame()
        card.setStyleSheet("QFrame { background: #1C1E22; border-radius: 12px; border: 1px solid #2C3035; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl1 = QLabel("Course / Class")
        lbl1.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.inp_session = QComboBox()
        self.inp_session.setEditable(True)
        self.inp_session.addItems(["CS101 Morning Lecture", "IT Lab Batch A", "ECE Tutorial", "Workshop Session"])
        self.inp_session.setStyleSheet(FIELD_STYLE)

        lbl_subject = QLabel("Subject / Module")
        lbl_subject.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none; margin-top: 10px;")
        self.inp_subject = QComboBox()
        self.inp_subject.setEditable(True)
        self.inp_subject.addItems(["Data Structures", "DBMS", "Signals", "Mathematics", "Other"])
        self.inp_subject.setStyleSheet(FIELD_STYLE)
        
        lbl_time = QLabel("Time Slot")
        lbl_time.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none; margin-top: 10px;")
        self.inp_time_slot = QComboBox()
        self.inp_time_slot.setEditable(True)
        self.inp_time_slot.addItems(["10:00 AM - 10:45 AM", "11:00 AM - 11:45 AM", "12:00 PM - 12:45 PM"])
        self.inp_time_slot.setStyleSheet(FIELD_STYLE)

        lbl_faculty = QLabel("Faculty / Invigilator")
        lbl_faculty.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none; margin-top: 10px;")
        self.inp_faculty = QLineEdit()
        self.inp_faculty.setPlaceholderText("e.g. Prof. Sharma")
        self.inp_faculty.setStyleSheet(FIELD_STYLE)

        lbl_room = QLabel("Room / Lab")
        lbl_room.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none; margin-top: 10px;")
        self.inp_room = QComboBox()
        self.inp_room.setEditable(True)
        self.inp_room.addItems(["Room 201", "Lab 1", "Seminar Hall", "Online", "Other"])
        self.inp_room.setStyleSheet(FIELD_STYLE)

        lbl_session_type = QLabel("Session Type")
        lbl_session_type.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none; margin-top: 10px;")
        self.inp_session_type = QComboBox()
        self.inp_session_type.setEditable(True)
        self.inp_session_type.addItems(["Lecture", "Lab", "Tutorial", "Exam", "Workshop", "Other"])
        self.inp_session_type.setStyleSheet(FIELD_STYLE)
        
        card_layout.addWidget(lbl1)
        card_layout.addWidget(self.inp_session)
        card_layout.addWidget(lbl_subject)
        card_layout.addWidget(self.inp_subject)
        card_layout.addWidget(lbl_time)
        card_layout.addWidget(self.inp_time_slot)
        card_layout.addWidget(lbl_faculty)
        card_layout.addWidget(self.inp_faculty)
        card_layout.addWidget(lbl_room)
        card_layout.addWidget(self.inp_room)
        card_layout.addWidget(lbl_session_type)
        card_layout.addWidget(self.inp_session_type)
        left_layout.addWidget(card)

        # Live Activity Log widget
        log_card = QFrame()
        log_card.setStyleSheet("QFrame { background: #111214; border-radius: 12px; border: 1px solid #2C3035; }")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(10, 10, 10, 10)
        
        log_title = QLabel("Live Authentications")
        log_title.setStyleSheet("color: #00D2FF; font-weight: bold; font-size: 14px; border: none;")
        log_layout.addWidget(log_title)
        
        self.live_table = QTableWidget()
        self.live_table.setColumnCount(1)
        self.live_table.setHorizontalHeaderLabels(["Student Name"])
        self.live_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.live_table.verticalHeader().setVisible(False)
        self.live_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.live_table.setStyleSheet("""
            QTableWidget { background: #1C1E22; border: none; color: #E0E6ED; font-size: 12px; }
            QTableWidget::item { padding: 4px; border-bottom: 1px solid #2C3035; }
            QHeaderView::section { background: #111214; color: #8B949E; border: none; border-bottom: 1px solid #2C3035; }
        """)
        log_layout.addWidget(self.live_table)
        left_layout.addWidget(log_card)

        # Action Buttons
        self.btn_start = QPushButton("Start Live Scanner")
        self.btn_start.setStyleSheet(BTN_START)
        self.btn_start.clicked.connect(self._start_session)
        
        self.btn_stop = QPushButton("End Session & Save")
        self.btn_stop.setStyleSheet(BTN_STOP)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._end_and_save)

        self.lbl_session_status = QLabel("Session idle.")
        self.lbl_session_status.setWordWrap(True)
        self.lbl_session_status.setStyleSheet("color: #8B949E; font-size: 13px; border: none;")

        self.save_progress = QProgressBar()
        self.save_progress.setRange(0, 100)
        self.save_progress.setValue(0)
        self.save_progress.hide()
        self.save_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2C3035; border-radius: 7px; text-align: center;
                background: #111214; color: #FFFFFF; height: 16px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00D2FF, stop:1 #98C379);
                border-radius: 6px;
            }
        """)
        
        left_layout.addWidget(self.btn_start)
        left_layout.addWidget(self.btn_stop)
        left_layout.addWidget(self.lbl_session_status)
        left_layout.addWidget(self.save_progress)
        root.addWidget(left_widget)

        # ── RIGHT PANEL (Embedded Camera View) ──
        right_layout = QVBoxLayout()
        right_layout.setSpacing(16)
        
        self.lbl_camera = QLabel("Camera Feed Offline\nPress Start to activate session scanner.")
        self.lbl_camera.setAlignment(Qt.AlignCenter)
        self.lbl_camera.setStyleSheet("""
            background: #0D0E10; border-radius: 12px; border: 2px dashed #2C3035; 
            color: #5C6370; font-size: 16px; font-weight: bold;
        """)
        self.lbl_camera.setMinimumSize(640, 480)
        right_layout.addWidget(self.lbl_camera)
        
        root.addLayout(right_layout, stretch=1)

    def _start_session(self):
        self._current_session_full_name = self._compose_session_name()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_session_status.setText("Live scanner running. Detected students will appear below.")
        self.lbl_session_status.setStyleSheet("color: #00D2FF; font-size: 13px; border: none;")
        self.inp_session.setEnabled(False)
        self.inp_subject.setEnabled(False)
        self.inp_time_slot.setEnabled(False)
        self.inp_faculty.setEnabled(False)
        self.inp_room.setEnabled(False)
        self.inp_session_type.setEnabled(False)
        
        self._staged_students = []
        self.live_table.setRowCount(0)
        
        # Load Encodings
        from core.encoding_loader import load_encodings
        student_ids, encodings = load_encodings()
        if not student_ids:
            QMessageBox.critical(self, "Error", "No student encodings found. Please enroll and train first.")
            self._reset_ui()
            return

        student_names = self._load_student_names()
            
        self.thread = FaceRecognitionThread(student_ids, encodings, student_names)
        self.thread.change_pixmap_signal.connect(self._update_image)
        self.thread.student_identified_signal.connect(self._on_student_identified)
        self.thread.start()

    def _update_image(self, qt_img):
        scaled_img = qt_img.scaled(self.lbl_camera.width(), self.lbl_camera.height(), Qt.KeepAspectRatio)
        self.lbl_camera.setPixmap(QPixmap.fromImage(scaled_img))
        self.lbl_camera.setStyleSheet("background: #000000; border-radius: 12px; border: 1px solid #00D2FF;")

    def _compose_session_name(self):
        class_name = self.inp_session.currentText().strip() or "General"
        subject = self.inp_subject.currentText().strip()
        time_slot = self.inp_time_slot.currentText().strip()
        faculty = self.inp_faculty.text().strip()
        room = self.inp_room.currentText().strip()
        session_type = self.inp_session_type.currentText().strip()

        parts = [class_name]
        if subject:
            parts.append(subject)
        if session_type:
            parts.append(session_type)
        if room:
            parts.append(room)
        if faculty:
            parts.append(faculty)
        if time_slot:
            parts.append(time_slot)
        return " | ".join(parts)

    def _load_student_names(self):
        with get_connection() as conn:
            rows = conn.execute("SELECT student_id, name FROM students").fetchall()
        return {row["student_id"]: row["name"] for row in rows}

    def _on_student_identified(self, student_id, display_name):
        ts = datetime.datetime.now().strftime("%I:%M:%S %p")
        self._staged_students.append((student_id, display_name, ts))
        
        row_idx = self.live_table.rowCount()
        self.live_table.insertRow(row_idx)
        
        item_name = QTableWidgetItem(display_name)
        item_name.setForeground(QColor("#98C379")) # Green success color
        self.live_table.setItem(row_idx, 0, item_name)
        self.live_table.scrollToBottom()

    def _end_and_save(self):
        self.btn_stop.setEnabled(False)
        self.lbl_session_status.setText("Stopping live feed and saving attendance...")
        self.lbl_session_status.setStyleSheet("color: #E5C07B; font-size: 13px; border: none;")

        if self.thread:
            self.thread.stop()
            self.thread = None
            
        self.lbl_camera.clear()
        self.lbl_camera.setText("Generating Secure Attendance Output...")
        self.lbl_camera.setStyleSheet("""
            background: #0D0E10; border-radius: 12px; border: 2px dashed #98C379; 
            color: #98C379; font-size: 16px; font-weight: bold;
        """)

        self._save_queue = list(self._staged_students)
        self._save_total = max(1, len(self._save_queue))
        self._pending_export_count = 0
        self._last_session_saved_count = 0
        self._save_started_at = datetime.datetime.now()
        self.save_progress.setValue(0)
        self.save_progress.show()
        QApplication.processEvents()
        QTimer.singleShot(80, self._process_save_step)

    def _update_save_progress(self, value, text):
        elapsed = max(1.0, (datetime.datetime.now() - self._save_started_at).total_seconds())
        if value <= 0:
            eta_text = "ETA: calculating"
        else:
            eta_seconds = max(0, int((elapsed / max(1, value)) * (100 - value)))
            eta_text = f"ETA: ~{eta_seconds}s"

        self.lbl_session_status.setText(f"{text}  {eta_text}")
        self.lbl_session_status.setStyleSheet("color: #E5C07B; font-size: 13px; border: none;")
        self.save_progress.setValue(value)
        QApplication.processEvents()

    def _process_save_step(self):
        if self._save_queue:
            student_id, display_name, _ts = self._save_queue.pop(0)
            try:
                if log_attendance(student_id, self._current_session_full_name):
                    self._pending_export_count += 1
            except Exception as exc:
                self.save_progress.hide()
                QMessageBox.critical(self, "Save Failed", f"Attendance could not be saved.\n\n{exc}")
                self._reset_ui()
                return

            processed = self._save_total - len(self._save_queue)
            progress = min(90, int((processed / self._save_total) * 85) + 10)
            self._update_save_progress(progress, f"Saving {display_name} ({processed}/{self._save_total})...")
            QTimer.singleShot(50, self._process_save_step)
            return

        self._last_session_saved_count = self._pending_export_count
        self._update_save_progress(100, "Finalizing session and preparing export options...")
        QTimer.singleShot(120, self._finish_save_sequence)

    def _finish_save_sequence(self):
        self.save_progress.hide()
        self._reset_ui()
            
    def _reset_ui(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._save_queue = []
        self._save_total = 0
        self._pending_export_count = 0
        self.save_progress.hide()
        self.save_progress.setValue(0)
        self.inp_session.setEnabled(True)
        self.inp_subject.setEnabled(True)
        self.inp_time_slot.setEnabled(True)
        self.inp_faculty.setEnabled(True)
        self.inp_room.setEnabled(True)
        self.inp_session_type.setEnabled(True)
        self.lbl_session_status.setText(
            f"Session saved successfully. {self._last_session_saved_count} attendance record(s) marked."
        )
        self.lbl_session_status.setStyleSheet("color: #98C379; font-size: 13px; border: none;")
        self.lbl_camera.clear()
        self.lbl_camera.setText("Camera Feed Offline\nPress Start to activate session scanner.")
        self.lbl_camera.setStyleSheet("""
            background: #0D0E10; border-radius: 12px; border: 2px dashed #2C3035; 
            color: #5C6370; font-size: 16px; font-weight: bold;
        """)

    def hideEvent(self, event):
        if self.thread:
            self.thread.stop()
            self.thread = None
        super().hideEvent(event)
