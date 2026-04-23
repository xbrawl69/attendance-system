import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from database.db_handler import get_connection

def log_attendance(student_id, session_name="General"):
    today = date.today().isoformat()
    now   = datetime.now().isoformat(sep=" ", timespec="seconds")

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT attendance_id FROM attendance WHERE student_id=? AND date=? AND session_name=?",
            (student_id, today, session_name)
        ).fetchone()

        if existing:
            print(f"[SKIP] {student_id} already marked for '{session_name}' today.")
            return False

        conn.execute(
            "INSERT INTO attendance (student_id, session_name, date, timestamp, status) VALUES (?,?,?,?,?)",
            (student_id, session_name, today, now, "Present")
        )
        conn.commit()
        print(f"[LOG] Marked: {student_id} | {session_name} | {now}")
        return True


def get_attendance_today(session_name=None):
    today = date.today().isoformat()
    with get_connection() as conn:
        if session_name:
            rows = conn.execute(
                "SELECT a.student_id, s.name, s.roll_number, a.timestamp, a.session_name FROM attendance a JOIN students s ON a.student_id=s.student_id WHERE a.date=? AND a.session_name=? ORDER BY a.timestamp",
                (today, session_name)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.student_id, s.name, s.roll_number, a.timestamp, a.session_name FROM attendance a JOIN students s ON a.student_id=s.student_id WHERE a.date=? ORDER BY a.timestamp",
                (today,)
            ).fetchall()
    return [dict(row) for row in rows]


def get_attendance_report(from_date=None, to_date=None):
    with get_connection() as conn:
        if from_date and to_date:
            rows = conn.execute(
                "SELECT a.student_id, s.name, s.roll_number, s.department, a.date, a.session_name, a.timestamp, a.status FROM attendance a JOIN students s ON a.student_id=s.student_id WHERE a.date BETWEEN ? AND ? ORDER BY a.date DESC",
                (from_date, to_date)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.student_id, s.name, s.roll_number, s.department, a.date, a.session_name, a.timestamp, a.status FROM attendance a JOIN students s ON a.student_id=s.student_id ORDER BY a.date DESC"
            ).fetchall()
    return [dict(row) for row in rows]
