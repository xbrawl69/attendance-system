import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

DB_PATH        = os.path.join(ROOT_DIR, "database", "attendance.db")
STUDENT_IMAGES = os.path.join(ROOT_DIR, "data", "student_images")
ENCODINGS_PATH = os.path.join(ROOT_DIR, "models", "face_encodings.csv")
MODEL_PATH     = os.path.join(ROOT_DIR, "models", "face_recognition_model.mat")
APP_VERSION    = "v1.0"

CAMERA_INDEX         = 0
SIMILARITY_THRESHOLD = 0.75
SESSION_DURATION_MIN = 5
