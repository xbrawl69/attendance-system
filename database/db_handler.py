import sqlite3
import os
import sys
import shutil
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import DB_PATH, STUDENT_IMAGES, ENCODINGS_PATH

STUDENT_COLUMN_DEFINITIONS = {
    "course": "TEXT",
    "academic_year": "TEXT",
    "semester": "TEXT",
    "section": "TEXT",
    "email": "TEXT",
    "phone": "TEXT",
}

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _ensure_student_columns(conn):
    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(students)").fetchall()
    }

    for column_name, column_type in STUDENT_COLUMN_DEFINITIONS.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE students ADD COLUMN {column_name} {column_type}")

def initialize_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        schema = f.read()
    with get_connection() as conn:
        conn.executescript(schema)
        _ensure_student_columns(conn)
        conn.commit()
    print("Database initialized successfully.")

def reset_application_data():
    if os.path.isdir(STUDENT_IMAGES):
        for entry in os.listdir(STUDENT_IMAGES):
            entry_path = os.path.join(STUDENT_IMAGES, entry)
            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path, ignore_errors=True)
            elif os.path.exists(entry_path):
                os.remove(entry_path)
    else:
        os.makedirs(STUDENT_IMAGES, exist_ok=True)

    with get_connection() as conn:
        conn.execute("DELETE FROM attendance")
        conn.execute("DELETE FROM students")
        conn.commit()

    # Keep trained model files on disk, but clear the live student map so deleted
    # students are not treated as active enrollments.
    map_path = ENCODINGS_PATH.replace("face_encodings.csv", "student_map.json")
    if os.path.exists(map_path):
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

if __name__ == "__main__":
    initialize_db()
