import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from utils.config import ENCODINGS_PATH
from database.db_handler import get_connection

def load_encodings():
    yml_path = ENCODINGS_PATH.replace('face_encodings.csv', 'face_encodings.yml')
    map_path = ENCODINGS_PATH.replace('face_encodings.csv', 'student_map.json')
    
    if not os.path.exists(yml_path):
        print("[WARNING] face_encodings.yml not found.")
        print("          Run enrollment to generate LBPH models.")
        return [], None

    import cv2, json
    if not hasattr(cv2, "face"):
        print("[ERROR] OpenCV contrib modules are unavailable. Install opencv-contrib-python.")
        return [], None

    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(yml_path)
        with open(map_path, 'r') as f:
            student_map = json.load(f)

        with get_connection() as conn:
            active_ids = {
                row["student_id"]
                for row in conn.execute("SELECT student_id FROM students").fetchall()
            }

        student_map = {
            label: student_id
            for label, student_id in student_map.items()
            if student_id in active_ids
        }

        if not student_map:
            print("[WARNING] No active enrolled students found in database.")
            return [], None
            
        print(f"[INFO] Loaded LBPH model for {len(student_map)} students.")
        return student_map, recognizer
    except Exception as e:
        print(f"[ERROR] Failed to load LBPH face model: {e}")
        return [], None
