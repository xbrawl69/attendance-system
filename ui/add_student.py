import os
import sys
import cv2
import uuid
import time
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox, QComboBox, QProgressBar, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap
from database.db_handler import get_connection
from utils.config import STUDENT_IMAGES
from core.face_recognition_engine import face_cascade, predict_lbph_match
from core.encoding_loader import load_encodings

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

BTN_PRIMARY = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00D2FF, stop:1 #3A7BD5);
        color: white; border: none;
        border-radius: 8px; padding: 11px 24px;
        font-size: 13px; font-weight: bold;
    }
    QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3A7BD5, stop:1 #00D2FF); }
    QPushButton:disabled { background: #3A3F44; color: #7F8C8D; }
"""

BTN_SECONDARY = """
    QPushButton {
        background: #2C3035; color: #E0E6ED; border: 1px solid #3A3F44;
        border-radius: 8px; padding: 11px 24px;
        font-size: 13px; font-weight: bold;
    }
    QPushButton:hover { background: #3A3F44; }
    QPushButton:disabled { background: #1E2124; color: #7F8C8D; border: 1px solid #2C3035; }
"""

CARD_STYLE = "QFrame { background: #1C1E22; border-radius: 12px; border: 1px solid #2C3035; }"

MESH_GROUPS = [
    list(range(0, 17)),
    list(range(17, 22)),
    list(range(22, 27)),
    list(range(27, 31)),
    list(range(31, 36)),
    [36, 37, 38, 39, 40, 41, 36],
    [42, 43, 44, 45, 46, 47, 42],
    [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 48],
    [60, 61, 62, 63, 64, 65, 66, 67, 60],
]

MESH_CONNECTIONS = [
    (0, 17), (16, 26), (21, 27), (22, 27), (27, 30), (30, 33),
    (31, 48), (35, 54), (33, 51), (48, 57), (54, 57), (36, 39),
    (42, 45), (39, 42), (31, 36), (35, 45), (48, 33), (54, 33),
    (3, 31), (13, 35), (8, 57), (19, 37), (24, 44), (38, 41),
    (43, 46), (50, 61), (52, 63), (56, 65), (58, 67),
]

FOREHEAD_CONNECTIONS = [
    ("jaw_left", "forehead_left"),
    ("jaw_left_upper", "forehead_left_mid"),
    ("brow_left_outer", "forehead_left"),
    ("brow_left_inner", "forehead_left_mid"),
    ("brow_bridge_left", "forehead_center"),
    ("brow_bridge_right", "forehead_center"),
    ("brow_right_inner", "forehead_right_mid"),
    ("brow_right_outer", "forehead_right"),
    ("jaw_right_upper", "forehead_right_mid"),
    ("jaw_right", "forehead_right"),
    ("forehead_left", "forehead_left_mid"),
    ("forehead_left_mid", "forehead_center"),
    ("forehead_center", "forehead_right_mid"),
    ("forehead_right_mid", "forehead_right"),
]

class AddStudentPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #141619; color: #E0E6ED;")
        self.camera_index = 0
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.captured_count = 0
        self.is_capturing = False
        self._current_student_id = None
        self._current_image_folder = None
        self._capture_queue = []
        self._async_landmarks = None
        self._async_face_box = None
        self._is_landmarking = False
        self._facemark = None
        self._facemark_warning_shown = False
        self._frame_index = 0
        self._last_faces = []
        self._last_capture_time = 0.0
        self._last_good_face = None
        self._face_loss_counter = 0
        self._capture_block_until = 0.0
        self._duplicate_student_map = {}
        self._duplicate_recognizer = None
        self._student_name_lookup = {}
        self._duplicate_match_id = None
        self._duplicate_match_streak = 0
        self._waiting_for_new_face = False
        self._unknown_face_streak = 0
        self._verifying_new_face = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        title = QLabel("Add New Student")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        
        self.cam_dropdown = QComboBox()
        self.cam_dropdown.addItems(["Camera 0 (Laptop)", "Camera 1 (External)"])
        self.cam_dropdown.setStyleSheet(FIELD_STYLE)
        self.cam_dropdown.setFixedWidth(180)
        self.cam_dropdown.currentIndexChanged.connect(self._change_camera)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.cam_dropdown)
        layout.addLayout(header_layout)

        subtitle = QLabel("Fill details and capture face angles (frontal, left, right) for deep AI training.")
        subtitle.setStyleSheet("color: #8B949E; font-size: 14px;")
        layout.addWidget(subtitle)

        # Form card
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)
        
        form_card = QFrame()
        form_card.setStyleSheet(CARD_STYLE)
        form_card.setFixedWidth(440)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(16)

        def field_row(label_text, placeholder):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setStyleSheet(FIELD_STYLE)
            return lbl, inp

        def editable_combo(options):
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(options)
            combo.setInsertPolicy(QComboBox.NoInsert)
            combo.setStyleSheet(FIELD_STYLE)
            return combo

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        name_lbl, self.inp_name = field_row("FULL NAME", "e.g. Rahul Sharma")
        roll_lbl, self.inp_roll = field_row("ROLL NUMBER", "e.g. CS2021001")
        email_lbl, self.inp_email = field_row("EMAIL", "e.g. rahul@college.edu")
        phone_lbl, self.inp_phone = field_row("PHONE", "e.g. +91 9876543210")

        dept_lbl = QLabel("DEPARTMENT")
        dept_lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.inp_dept = editable_combo([
            "Computer Science", "Information Technology", "Electronics", "Mechanical", "Civil", "Other"
        ])

        course_lbl = QLabel("COURSE")
        course_lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.inp_course = editable_combo(["B.Tech", "M.Tech", "BCA", "MCA", "BSc", "MSc", "MBA", "Other"])

        semester_lbl = QLabel("SEMESTER")
        semester_lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.inp_semester = editable_combo([
            "Semester 1", "Semester 2", "Semester 3", "Semester 4",
            "Semester 5", "Semester 6", "Semester 7", "Semester 8", "Other"
        ])

        fields = [
            (0, 0, name_lbl, self.inp_name),
            (0, 1, roll_lbl, self.inp_roll),
            (1, 0, dept_lbl, self.inp_dept),
            (1, 1, course_lbl, self.inp_course),
            (2, 0, semester_lbl, self.inp_semester),
            (2, 1, email_lbl, self.inp_email),
            (3, 0, phone_lbl, self.inp_phone),
        ]

        for row, col, label_widget, input_widget in fields:
            cell_layout = QVBoxLayout()
            cell_layout.setSpacing(6)
            cell_layout.addWidget(label_widget)
            cell_layout.addWidget(input_widget)
            grid.addLayout(cell_layout, row, col)

        form_layout.addLayout(grid)

        form_layout.addStretch()

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self.lbl_status.setWordWrap(True)
        form_layout.addWidget(self.lbl_status)

        # AI Training Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2C3035; border-radius: 6px; 
                text-align: center; color: white; font-weight: bold; font-size: 11px;
                background: #111214; height: 18px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00D2FF, stop:1 #3A7BD5);
                border-radius: 5px;
            }
        """)
        self.progress_bar.hide()
        form_layout.addWidget(self.progress_bar)

        self.btn_save = QPushButton("Save Details")
        self.btn_save.setStyleSheet(BTN_PRIMARY)
        self.btn_save.clicked.connect(self._save_student)
        form_layout.addWidget(self.btn_save)

        self.btn_capture = QPushButton("Start Capture (50 frames)")
        self.btn_capture.setStyleSheet(BTN_SECONDARY)
        self.btn_capture.setEnabled(False)
        self.btn_capture.clicked.connect(self._start_capture)
        form_layout.addWidget(self.btn_capture)

        content_layout.addWidget(form_card)

        # Video feed card
        video_card = QFrame()
        video_card.setStyleSheet("QFrame { background: #111214; border-radius: 12px; border: 1px solid #2C3035; }")
        video_layout = QVBoxLayout(video_card)
        video_layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_video = QLabel("Camera Feed Initializing...")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setStyleSheet("color: #8B949E; font-size: 16px; border: none;")
        self.lbl_video.setMinimumSize(680, 500)
        video_layout.addWidget(self.lbl_video)
        
        content_layout.addWidget(video_card)
        layout.addLayout(content_layout)
        layout.addStretch()
        
        self.lbl_video.setText("Camera is off.\nOpen Add Student to start preview.")

    def _change_camera(self, index):
        self.camera_index = index
        self._start_camera_preview()

    def _start_camera_preview(self):
        if self.cap is not None:
            self.cap.release()
        self.timer.stop()
        
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)
            
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.lbl_video.setText("Camera Ready")
            self.timer.start(33)
        else:
            self.lbl_video.setText("Error: Camera not found.")

    def _save_student(self):
        name = self.inp_name.text().strip()
        roll = self.inp_roll.text().strip()
        dept = self.inp_dept.currentText().strip()
        course = self.inp_course.currentText().strip()
        semester = self.inp_semester.currentText().strip()
        email = self.inp_email.text().strip()
        phone = self.inp_phone.text().strip()

        if not name or not roll:
            QMessageBox.warning(self, "Missing Fields", "Please fill in Name and Roll Number.")
            return

        student_id = "STU" + str(uuid.uuid4())[:8].upper()
        image_folder = os.path.join(STUDENT_IMAGES, student_id)
        os.makedirs(image_folder, exist_ok=True)

        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO students (
                        student_id, name, roll_number, department, course,
                        academic_year, semester, section, email, phone, image_folder
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        student_id, name, roll, dept, course,
                        "", semester, "", email, phone, image_folder
                    )
                )
                conn.commit()

            self._current_student_id = student_id
            self._current_image_folder = image_folder
            self.lbl_status.setText(f"✓ Saved {name}. Look at the camera & start capture.")
            self.lbl_status.setStyleSheet("color: #00D2FF; font-size: 13px; font-weight: bold; border: none;")
            self.btn_capture.setEnabled(True)
            self.btn_save.setEnabled(False)
            self.inp_name.setEnabled(False)
            self.inp_roll.setEnabled(False)
            self.inp_dept.setEnabled(False)
            self.inp_course.setEnabled(False)
            self.inp_semester.setEnabled(False)
            self.inp_email.setEnabled(False)
            self.inp_phone.setEnabled(False)

        except Exception as e:
            if "UNIQUE constraint" in str(e):
                QMessageBox.warning(self, "Duplicate", "Roll number already exists.")
            else:
                QMessageBox.critical(self, "Error", str(e))

    def _start_capture(self):
        if not self._current_student_id: return
        self.captured_count = 0
        self.is_capturing = True
        self._capture_queue = []
        self._last_capture_time = 0.0
        self._capture_block_until = 0.0
        self._duplicate_match_id = None
        self._duplicate_match_streak = 0
        self._waiting_for_new_face = False
        self._unknown_face_streak = 0
        self._verifying_new_face = True
        self._load_duplicate_guard()
        self.btn_capture.setEnabled(False)
        self.lbl_status.setText("Verifying face... checking this person is not already enrolled.")
        self.lbl_status.setStyleSheet("color: #E5C07B; font-size: 13px; font-weight: bold; border: none;")

    def _load_duplicate_guard(self):
        self._duplicate_student_map, self._duplicate_recognizer = load_encodings()
        with get_connection() as conn:
            rows = conn.execute("SELECT student_id, name FROM students").fetchall()
        self._student_name_lookup = {row["student_id"]: row["name"] for row in rows}

    def _restart_capture_due_to_duplicate(self, student_id):
        self.captured_count = 0
        self._capture_queue = []
        self._last_capture_time = 0.0
        self._duplicate_match_id = None
        self._duplicate_match_streak = 0
        self._capture_block_until = time.time() + 0.8
        self._waiting_for_new_face = True
        self._unknown_face_streak = 0
        self._verifying_new_face = True

        student_name = self._student_name_lookup.get(student_id, student_id)
        self.lbl_status.setText(
            f"Duplicate alert: {student_name} is already enrolled. Capture restarted at 0 frames."
        )
        self.lbl_status.setStyleSheet("color: #E06C75; font-size: 13px; font-weight: bold; border: none;")

    def _check_duplicate_enrollment(self, frame, face_bbox):
        if not self._duplicate_student_map or self._duplicate_recognizer is None:
            return None

        x, y, w, h = face_bbox
        pad_y = int(h * 0.10)
        pad_x = int(w * 0.10)
        y1, y2 = max(0, y-pad_y), min(frame.shape[0], y+h+pad_y)
        x1, x2 = max(0, x-pad_x), min(frame.shape[1], x+w+pad_x)
        face_crop_bgr = frame[y1:y2, x1:x2]
        if face_crop_bgr.size == 0:
            return None

        face_crop_rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB)
        student_id, confidence, distance = predict_lbph_match(
            face_crop_rgb,
            self._duplicate_student_map,
            self._duplicate_recognizer,
            distance_threshold=92,
        )
        if student_id == "Unknown" or (confidence < 0.45 and (distance is None or distance > 92)):
            self._duplicate_match_id = None
            self._duplicate_match_streak = 0
            return None

        if self._duplicate_match_id == student_id:
            self._duplicate_match_streak += 1
        else:
            self._duplicate_match_id = student_id
            self._duplicate_match_streak = 1

        if self._duplicate_match_streak >= 3:
            return student_id
        return None

    def _face_is_ready_for_capture(self, frame, face_bbox):
        if not self._duplicate_student_map or self._duplicate_recognizer is None:
            return True

        x, y, w, h = face_bbox
        pad_y = int(h * 0.10)
        pad_x = int(w * 0.10)
        y1, y2 = max(0, y-pad_y), min(frame.shape[0], y+h+pad_y)
        x1, x2 = max(0, x-pad_x), min(frame.shape[1], x+w+pad_x)
        face_crop_bgr = frame[y1:y2, x1:x2]
        if face_crop_bgr.size == 0:
            return False

        face_crop_rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB)
        matched_student_id, confidence, distance = predict_lbph_match(
            face_crop_rgb,
            self._duplicate_student_map,
            self._duplicate_recognizer,
            distance_threshold=92,
        )

        is_known_face = matched_student_id != "Unknown" and (
            confidence >= 0.45 or (distance is not None and distance <= 92)
        )

        if is_known_face:
            self._unknown_face_streak = 0
            if time.time() >= self._capture_block_until:
                duplicate_student_id = self._check_duplicate_enrollment(frame, face_bbox)
                if duplicate_student_id:
                    self._restart_capture_due_to_duplicate(duplicate_student_id)
            return False

        self._duplicate_match_id = None
        self._duplicate_match_streak = 0

        if self._waiting_for_new_face:
            self._unknown_face_streak += 1
            if self._unknown_face_streak >= 6:
                self._waiting_for_new_face = False
                self._verifying_new_face = True
                self.lbl_status.setText("Different face detected. Verifying before capture starts...")
                self.lbl_status.setStyleSheet("color: #E5C07B; font-size: 13px; font-weight: bold; border: none;")
                return False

            self.lbl_status.setText("Already captured student detected. Waiting for a different face...")
            self.lbl_status.setStyleSheet("color: #E06C75; font-size: 13px; font-weight: bold; border: none;")
            return False

        self._unknown_face_streak += 1
        if self._verifying_new_face:
            if self._unknown_face_streak >= 8:
                self._verifying_new_face = False
                self._capture_block_until = 0.0
                self._unknown_face_streak = 0
                self.lbl_status.setText("Verification complete. Safe to capture this new student now.")
                self.lbl_status.setStyleSheet("color: #98C379; font-size: 13px; font-weight: bold; border: none;")
                return True

            self.lbl_status.setText("Verifying new face... please keep only the new student in frame.")
            self.lbl_status.setStyleSheet("color: #E5C07B; font-size: 13px; font-weight: bold; border: none;")
            return False

        return True

    def _draw_hud(self, frame, x, y, w, h):
        color = (0, 220, 255)
        thickness = 2
        length = max(18, min(w, h) // 7)
        # Top-left
        cv2.line(frame, (x, y), (x + length, y), color, thickness)
        cv2.line(frame, (x, y), (x, y + length), color, thickness)
        # Top-right
        cv2.line(frame, (x + w, y), (x + w - length, y), color, thickness)
        cv2.line(frame, (x + w, y), (x + w, y + length), color, thickness)
        # Bottom-left
        cv2.line(frame, (x, y + h), (x + length, y + h), color, thickness)
        cv2.line(frame, (x, y + h), (x, y + h - length), color, thickness)
        # Bottom-right
        cv2.line(frame, (x + w, y + h), (x + w - length, y + h), color, thickness)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - length), color, thickness)
        
        # Draw scanning crosshair
        center_x, center_y = x + w//2, y + h//2
        cv2.line(frame, (center_x, y + 10), (center_x, y + h - 10), (255, 255, 255), 1)
        cv2.line(frame, (x + 10, center_y), (x + w - 10, center_y), (255, 255, 255), 1)

    def _ensure_facemark(self):
        if self._facemark is not None:
            return self._facemark

        try:
            from utils.config import ROOT_DIR
            lbf_path = os.path.join(ROOT_DIR, "models", "lbfmodel.yaml")
            if not os.path.exists(lbf_path) or not hasattr(cv2, "face"):
                return None

            self._facemark = cv2.face.createFacemarkLBF()
            self._facemark.loadModel(lbf_path)
        except Exception as exc:
            self._facemark = None
            if not self._facemark_warning_shown:
                self._facemark_warning_shown = True
                self.lbl_status.setText(f"Preview mesh disabled: {exc}")
                self.lbl_status.setStyleSheet("color: #E5C07B; font-size: 13px; font-weight: bold; border: none;")

        return self._facemark

    def _smooth_faces(self, faces):
        if len(faces) != 1:
            self._last_faces = faces
            return faces

        if len(self._last_faces) != 1:
            self._last_faces = faces
            return faces

        (px, py, pw, ph) = self._last_faces[0]
        (x, y, w, h) = faces[0]
        alpha = 0.35
        smoothed = (
            int(px * (1 - alpha) + x * alpha),
            int(py * (1 - alpha) + y * alpha),
            int(pw * (1 - alpha) + w * alpha),
            int(ph * (1 - alpha) + h * alpha),
        )
        self._last_faces = [smoothed]
        return [smoothed]

    def _get_landmark_points(self, gray_frame, face_bbox):
        facemark = self._ensure_facemark()
        if facemark is None:
            return None

        import numpy as np

        x, y, w, h = face_bbox
        bbox = np.array([[x, y, w, h]], dtype=np.int32)

        try:
            ok, landmarks = facemark.fit(gray_frame, bbox)
        except Exception:
            return None

        if not ok or landmarks is None or len(landmarks) == 0:
            return None

        return [(int(pt[0]), int(pt[1])) for pt in landmarks[0][0]]

    def _build_extended_mesh(self, points):
        brow_left_outer = np.array(points[17], dtype=np.float32)
        brow_left_inner = np.array(points[19], dtype=np.float32)
        brow_bridge_left = np.array(points[21], dtype=np.float32)
        brow_bridge_right = np.array(points[22], dtype=np.float32)
        brow_right_inner = np.array(points[24], dtype=np.float32)
        brow_right_outer = np.array(points[26], dtype=np.float32)
        jaw_left = np.array(points[0], dtype=np.float32)
        jaw_left_upper = np.array(points[3], dtype=np.float32)
        jaw_right_upper = np.array(points[13], dtype=np.float32)
        jaw_right = np.array(points[16], dtype=np.float32)
        chin = np.array(points[8], dtype=np.float32)
        nose_bridge = np.array(points[27], dtype=np.float32)

        brow_mid = (brow_bridge_left + brow_bridge_right) / 2.0
        face_height = max(40.0, chin[1] - brow_mid[1])
        forehead_lift = face_height * 0.42
        outer_lift = forehead_lift * 0.9

        forehead_left = jaw_left * 0.18 + brow_left_outer * 0.82 + np.array([-8.0, -outer_lift], dtype=np.float32)
        forehead_left_mid = brow_left_inner + np.array([-4.0, -forehead_lift], dtype=np.float32)
        forehead_center = nose_bridge + np.array([0.0, -forehead_lift * 1.08], dtype=np.float32)
        forehead_right_mid = brow_right_inner + np.array([4.0, -forehead_lift], dtype=np.float32)
        forehead_right = jaw_right * 0.18 + brow_right_outer * 0.82 + np.array([8.0, -outer_lift], dtype=np.float32)

        return {
            "jaw_left": tuple(np.round(jaw_left).astype(int)),
            "jaw_left_upper": tuple(np.round(jaw_left_upper).astype(int)),
            "jaw_right_upper": tuple(np.round(jaw_right_upper).astype(int)),
            "jaw_right": tuple(np.round(jaw_right).astype(int)),
            "brow_left_outer": tuple(np.round(brow_left_outer).astype(int)),
            "brow_left_inner": tuple(np.round(brow_left_inner).astype(int)),
            "brow_bridge_left": tuple(np.round(brow_bridge_left).astype(int)),
            "brow_bridge_right": tuple(np.round(brow_bridge_right).astype(int)),
            "brow_right_inner": tuple(np.round(brow_right_inner).astype(int)),
            "brow_right_outer": tuple(np.round(brow_right_outer).astype(int)),
            "forehead_left": tuple(np.round(forehead_left).astype(int)),
            "forehead_left_mid": tuple(np.round(forehead_left_mid).astype(int)),
            "forehead_center": tuple(np.round(forehead_center).astype(int)),
            "forehead_right_mid": tuple(np.round(forehead_right_mid).astype(int)),
            "forehead_right": tuple(np.round(forehead_right).astype(int)),
        }

    def _draw_face_mesh(self, frame, points, face_bbox):
        if not points or len(points) < 68:
            return

        extended = self._build_extended_mesh(points)
        overlay = frame.copy()
        face_outline = [
            extended["jaw_left"],
            extended["forehead_left"],
            extended["forehead_left_mid"],
            extended["forehead_center"],
            extended["forehead_right_mid"],
            extended["forehead_right"],
            extended["jaw_right"],
            tuple(points[14]),
            tuple(points[12]),
            tuple(points[10]),
            tuple(points[8]),
            tuple(points[6]),
            tuple(points[4]),
            tuple(points[2]),
        ]
        hull = cv2.convexHull(np.array(face_outline, dtype=np.int32))
        cv2.fillConvexPoly(overlay, hull, (92, 124, 173))
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        for group in MESH_GROUPS:
            segment = [points[idx] for idx in group]
            cv2.polylines(frame, [np.array(segment, dtype=np.int32)], False, (220, 228, 242), 1, cv2.LINE_AA)

        for start_idx, end_idx in MESH_CONNECTIONS:
            cv2.line(frame, points[start_idx], points[end_idx], (210, 220, 235), 1, cv2.LINE_AA)

        for start_key, end_key in FOREHEAD_CONNECTIONS:
            cv2.line(frame, extended[start_key], extended[end_key], (210, 220, 235), 1, cv2.LINE_AA)

        for idx in [17, 19, 21, 22, 24, 26, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57, 8]:
            cv2.circle(frame, points[idx], 2, (255, 255, 255), -1, cv2.LINE_AA)

        for key in ["forehead_left", "forehead_left_mid", "forehead_center", "forehead_right_mid", "forehead_right"]:
            cv2.circle(frame, extended[key], 2, (255, 255, 255), -1, cv2.LINE_AA)

        x, y, w, h = face_bbox
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 220, 255), 1, cv2.LINE_AA)


    def _handle_capture_error(self, frame, message):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 255), -1) # Red tint
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        
        text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        text_x = (w - text_size[0]) // 2
        text_y = (h + text_size[1]) // 2
        
        cv2.rectangle(frame, (text_x - 10, text_y - text_size[1] - 10), 
                      (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
        cv2.putText(frame, message, (text_x, text_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        if not hasattr(self, 'error_beep_cooldown'):
            self.error_beep_cooldown = 0
            
        if time.time() - self.error_beep_cooldown > 1.5:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except:
                pass
            self.error_beep_cooldown = time.time()

    def _update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        ret, frame = self.cap.read()
        if not ret: return

        display_frame = frame.copy()
        
        if self.is_capturing:
            self._frame_index += 1
            scale_factor = 0.6
            if self._frame_index % 2 == 0 or not self._last_faces:
                small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
                gray_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                faces_small = face_cascade.detectMultiScale(
                    gray_small, scaleFactor=1.15, minNeighbors=5, minSize=(36, 36)
                )
                faces = [
                    (
                        int(fx / scale_factor),
                        int(fy / scale_factor),
                        int(fw / scale_factor),
                        int(fh / scale_factor),
                    )
                    for (fx, fy, fw, fh) in faces_small
                ]
                faces = self._smooth_faces(faces)
            else:
                faces = self._last_faces

            if len(faces) >= 1:
                self._last_good_face = faces[0]
                self._face_loss_counter = 0
            elif len(faces) == 0 and getattr(self, '_last_good_face', None) and getattr(self, '_face_loss_counter', 0) < 10:
                faces = [self._last_good_face]
                self._face_loss_counter += 1
            
            if len(faces) == 1:
                (x, y, w, h) = faces[0]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                landmark_points = self._get_landmark_points(gray, faces[0])
                self._draw_face_mesh(display_frame, landmark_points, faces[0])
                face_ready_for_capture = self._face_is_ready_for_capture(frame, faces[0])
            else:
                face_ready_for_capture = False

            if len(faces) == 0:
                self._unknown_face_streak = 0
                self.lbl_status.setText("Capture paused: face not clearly visible.")
                self.lbl_status.setStyleSheet("color: #E06C75; font-size: 13px; font-weight: bold; border: none;")
                self._handle_capture_error(display_frame, "ALERT: NO FACE VISIBLE. PAUSED.")
            elif len(faces) > 1:
                self._unknown_face_streak = 0
                self.lbl_status.setText("Capture paused: multiple faces detected.")
                self.lbl_status.setStyleSheet("color: #E06C75; font-size: 13px; font-weight: bold; border: none;")
                self._handle_capture_error(display_frame, "ALERT: MULTIPLE FACES DETECTED. PAUSED.")
            elif self._waiting_for_new_face or not face_ready_for_capture:
                self._handle_capture_error(display_frame, "ALREADY ENROLLED. SHOW NEW FACE.")
            else:
                self.error_beep_cooldown = 0
                self.lbl_status.setText("Capturing face samples. Hold center, then turn slightly left and right.")
                self.lbl_status.setStyleSheet("color: #E5C07B; font-size: 13px; font-weight: bold; border: none;")

                for (x, y, w, h) in faces:
                    self._draw_hud(display_frame, x, y, w, h)

                    now = time.time()
                    capture_interval = 0.12
                    if now - self._last_capture_time >= capture_interval:
                        self.captured_count += 1
                        self._last_capture_time = now

                        pad_y = int(h * 0.08)
                        pad_x = int(w * 0.08)
                        y1, y2 = max(0, y-pad_y), min(frame.shape[0], y+h+pad_y)
                        x1, x2 = max(0, x-pad_x), min(frame.shape[1], x+w+pad_x)
                        face_crop = frame[y1:y2, x1:x2]

                        img_name = f"{self._current_student_id}_{self.captured_count}.jpg"
                        img_path = os.path.join(self._current_image_folder, img_name)

                        self._capture_queue.append((img_path, face_crop))

                        if self.captured_count >= 50:
                            self.is_capturing = False
                            self._finish_capture()
                            break

            # Overlay stats
            cv2.rectangle(display_frame, (10, 10), (330, 50), (28, 30, 34), -1)
            cv2.putText(display_frame, f"FRAMES SECURED: {self.captured_count}/50", (20, 35), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 210, 255), 2)

        rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_img = qt_img.scaled(self.lbl_video.width(), self.lbl_video.height(), Qt.KeepAspectRatio)
        self.lbl_video.setPixmap(QPixmap.fromImage(scaled_img))

    def _finish_capture(self):
        self.lbl_status.setText("Images gathered. Training local CNN Neural Network...")
        self.lbl_status.setStyleSheet("color: #00D2FF; font-size: 13px; font-weight: bold; border: none;")
        self.btn_capture.setText("Training Model...")
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.progress_val = 0
        
        self.train_anim_timer = QTimer()
        self.train_anim_timer.timeout.connect(self._animate_training)
        self.train_anim_timer.start(50)
        
        def encode_task():
            import cv2
            for path, face_img in getattr(self, '_capture_queue', []):
                cv2.imwrite(path, face_img)
            self._capture_queue = []
            
            from core.face_recognition_engine import generate_python_encodings
            generate_python_encodings()
            self._training_done = True

        self._training_done = False
        import threading
        threading.Thread(target=encode_task, daemon=True).start()

    def _animate_training(self):
        if self.progress_val < 90 and not self._training_done:
            self.progress_val += 1
            self.progress_bar.setValue(self.progress_val)
        elif self._training_done:
            self.progress_val += 4
            self.progress_bar.setValue(min(100, self.progress_val))
            if self.progress_val >= 100:
                self.train_anim_timer.stop()
                self._complete_training()
                
    def _complete_training(self):
        self.lbl_status.setText("✓ Deep ML Training complete! Student enrolled securely.")
        self.lbl_status.setStyleSheet("color: #98C379; font-size: 13px; font-weight: bold; border: none;")
        self.btn_capture.setText("Enrollment Finished")
        QTimer.singleShot(3000, self._reset_form)

    def _reset_form(self):
        self.inp_name.clear()
        self.inp_roll.clear()
        self.inp_email.clear()
        self.inp_phone.clear()
        self.inp_name.setEnabled(True)
        self.inp_roll.setEnabled(True)
        self.inp_dept.setEnabled(True)
        self.inp_course.setEnabled(True)
        self.inp_semester.setEnabled(True)
        self.inp_email.setEnabled(True)
        self.inp_phone.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.btn_capture.setText("Start Capture (50 frames)")
        self.btn_capture.setEnabled(False)
        self.progress_bar.hide()
        self.lbl_status.setText("Ready.")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold; border: none;")
        self._current_student_id = None
        self._current_image_folder = None
        self._capture_queue = []
        self._last_capture_time = 0.0
        self._last_faces = []
        self._last_good_face = None
        self._face_loss_counter = 0
        self._capture_block_until = 0.0
        self._duplicate_student_map = {}
        self._duplicate_recognizer = None
        self._student_name_lookup = {}
        self._duplicate_match_id = None
        self._duplicate_match_streak = 0
        self._waiting_for_new_face = False
        self._unknown_face_streak = 0
        self._verifying_new_face = False
        
    def hideEvent(self, event):
        if self.cap:
            self.cap.release()
        self.timer.stop()
        super().hideEvent(event)
        
    def showEvent(self, event):
        self._start_camera_preview()
        super().showEvent(event)
