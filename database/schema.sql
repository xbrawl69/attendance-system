CREATE TABLE IF NOT EXISTS students (
    student_id    TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    roll_number   TEXT UNIQUE NOT NULL,
    department    TEXT,
    course        TEXT,
    academic_year TEXT,
    semester      TEXT,
    section       TEXT,
    email         TEXT,
    phone         TEXT,
    face_encoding BLOB,
    image_folder  TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT NOT NULL,
    session_name  TEXT,
    date          DATE NOT NULL,
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    status        TEXT DEFAULT "Present",
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);
