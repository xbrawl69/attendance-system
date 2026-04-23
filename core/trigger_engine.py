import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import threading
import schedule
from utils.config import SESSION_DURATION_MIN
from core.encoding_loader import load_encodings
from core.face_recognition_engine import run_recognition_session
from core.attendance_logger import log_attendance


def start_session(session_name="General"):
    print(f"[TRIGGER] Starting session: {session_name}")
    student_ids, encodings = load_encodings()

    if not student_ids:
        print("[TRIGGER] No encodings found. Enroll students first.")
        return

    def on_identify(sid):
        log_attendance(sid, session_name)

    duration = SESSION_DURATION_MIN * 60
    run_recognition_session(student_ids, encodings, on_identify, duration)
    print(f"[TRIGGER] Session ended: {session_name}")


def start_scheduled_trigger(time_str="09:00", session_name="Morning"):
    schedule.every().day.at(time_str).do(start_session, session_name=session_name)
    print(f"[SCHEDULER] Scheduled daily at {time_str} for '{session_name}'")
    while True:
        schedule.run_pending()
        time.sleep(30)


def start_trigger_in_background(time_str="09:00", session_name="Morning"):
    t = threading.Thread(
        target=start_scheduled_trigger,
        args=(time_str, session_name),
        daemon=True
    )
    t.start()
    print(f"[SCHEDULER] Background trigger active for {time_str}.")
    return t
