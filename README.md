# Attendance System v1.0

A desktop face-recognition attendance system built with Python, PyQt5, OpenCV, dlib, and SQLite.

It provides a complete workflow for:
- enrolling students with captured face samples,
- running a live attendance session through the camera,
- identifying enrolled students in real time,
- marking non-enrolled faces as `Unknown`,
- storing attendance records locally, and
- exporting attendance reports in CSV and PDF formats.

## Features

- Modern PyQt5 desktop interface
- Student enrollment form with camera preview
- Multi-frame face capture for training
- LBPH-based face recognition with local model storage
- Live attendance session screen with real-time detection
- Unknown face handling for people not enrolled in the system
- Dashboard with enrolled-student and attendance summary
- SQLite database for students and attendance records
- Date-filtered reports with CSV and PDF export
- Settings page for training-data access and app data reset

## Tech Stack

- Python 3
- PyQt5
- OpenCV (`opencv-contrib-python`)
- dlib
- `face-recognition`
- SQLite
- pandas
- reportlab

## Project Structure

```text
attendance-system/
|- core/                # Face recognition, encoding loading, attendance logging
|- database/            # SQLite schema, DB initialization, DB utilities
|- data/                # Captured student image folders
|- models/              # Trained model files and student map
|- ui/                  # PyQt5 pages: dashboard, add student, attendance, reports, settings
|- utils/               # Config and report export helpers
|- tests/               # Test package placeholder
|- main.py              # Application entry point
`- requirements.txt     # Python dependencies
```

## Main Modules

### 1. Dashboard
- Shows total enrolled students
- Shows today's attendance count
- Shows active sessions for the current day
- Displays recent attendance activity
- Displays registered students directory

### 2. Add Student
- Saves student details such as name, roll number, department, course, semester, email, and phone
- Opens a live camera preview
- Captures face samples for training
- Prevents duplicate enrollment when an already-known face is detected

### 3. Take Attendance
- Starts a live attendance scanner
- Detects faces from the camera feed
- Recognizes enrolled students in real time
- Marks unknown or non-enrolled people as `Unknown`
- Saves attendance once per student per session per day

### 4. Reports
- Shows attendance records in a table
- Filters records by date range
- Exports records as CSV
- Exports records as PDF

### 5. Settings
- Opens training-data folder
- Opens MATLAB scripts folder
- Clears live student and attendance data

## How Recognition Works

The system uses an LBPH face recognizer stored locally in the `models/` directory.

Current behavior:
- enrolled students are identified from the trained face model,
- far/smaller faces are handled more aggressively during live attendance preview,
- non-enrolled faces are shown as `Unknown`,
- deleted students are filtered out from live recognition through the active student map.

## Database

The app uses a local SQLite database at:

```text
database/attendance.db
```

Main tables:
- `students`
- `attendance`

The database is initialized automatically when the app starts.

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd attendance-system
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Run the Application

```bash
python main.py
```

On launch, the app:
1. initializes the database,
2. opens the PyQt5 desktop UI,
3. loads the main navigation with Dashboard, Add Student, Take Attendance, Reports, and Settings.

## Typical Workflow

### Enroll a Student
1. Open `Add Student`
2. Fill in student details
3. Save details
4. Start capture and record face samples
5. Allow the model data to be generated

### Mark Attendance
1. Open `Take Attendance`
2. Select or enter session details
3. Start live scanner
4. Let the system identify enrolled students
5. End the session and save records

### Export Reports
1. Open `Reports`
2. Choose a date range
3. Apply filter or show all records
4. Export as CSV or PDF

## Important Notes

- A working webcam is required for enrollment and live attendance.
- Good lighting improves face detection and recognition quality.
- First-time recognition depends on having valid captured face samples.
- The repository ignores:
  - `venv/`
  - `__pycache__/`
  - `database/attendance.db`
  - `data/student_images/`
  - `.env`

## Version

Current software version: `v1.0`

## Future Improvements

- Better camera selection and camera diagnostics
- More robust face-model retraining workflow
- Improved unknown-face review flow
- Admin authentication
- Cloud sync / online backup
- Attendance analytics dashboard

## License

This project is currently for academic / personal use unless you add a specific license file.
