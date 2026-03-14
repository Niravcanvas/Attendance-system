# 🎓 AI Attendance System

A face-recognition-based attendance system built with Flask and InsightFace. Capture a photo of a classroom, and it automatically marks attendance for recognized students.

---

## ✨ Features

- **Face Recognition** — Uses InsightFace (`buffalo_l` model) to detect and recognize student faces
- **Session Management** — Create class sessions per subject/teacher
- **Attendance Reports** — Export to CSV or Excel with filters
- **Student Management** — Add students with photos, roll numbers, department, and year
- **Role-Based Access** — Admin, Teacher, and Student roles with separate permissions
- **Defaulters Report** — Automatically flags students below 75% attendance

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask |
| Face AI | InsightFace (`buffalo_l`) |
| Database | SQLite |
| Image Processing | OpenCV, Pillow |
| Frontend | Jinja2 templates, HTML/CSS/JS |
| Export | openpyxl (Excel), csv (built-in) |

---

## 📁 Project Structure

```
Attendance System/
├── app.py                      # Main Flask application
├── config.py                   # Configuration (if used)
├── init_db.py                  # Database initializer
├── attendance_helpers.py       # Helper utilities
├── embedding_model.py          # Face embedding logic
├── encode_faces_insightfaces.py # Standalone face encoder
├── requirements.txt
├── attendance.db               # SQLite database (auto-created)
├── dataset/                    # Student face images (by student ID)
│   └── {student_id}/
│       ├── name.txt            # Student's name
│       └── *.jpg               # Face photos
├── encodings/                  # Numpy face embeddings
│   ├── index.json              # Maps student IDs → names + files
│   └── {student_id}.npy
├── static/
│   ├── css/
│   └── js/
├── Templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── capture.html
│   ├── students.html
│   ├── subjects.html
│   ├── attendance.html
│   ├── create_session.html
│   └── users.html
├── uploads/                    # Uploaded/captured images (auto-created)
├── logs/                       # App logs (auto-created)
└── timeline.json               # Recent recognition events
```

---

## 🚀 Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/attendance-system.git
cd "attendance-system"
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ InsightFace requires CMake and a C++ compiler. On macOS: `brew install cmake`. On Ubuntu: `sudo apt install cmake build-essential`.

### 4. Run the app

```bash
python app.py
```

The server starts at **http://localhost:5000**

---

## 🔑 Default Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Teacher | `teacher1` | `teacher123` |
| Student | `student1` | `student123` |

> ⚠️ Change these immediately in production.

---

## 📸 How Attendance Works

1. **Add Students** → Upload face photos via the Students page
2. **Encode Faces** → Click "Encode Faces" on the dashboard to generate embeddings
3. **Create a Session** → Select subject, teacher, date, and time
4. **Capture & Recognize** → Go to Capture page, take/upload a class photo, hit Recognize
5. **View Reports** → Attendance page shows per-session and per-student summaries

---

## 🗑️ Files You Can Delete

These files are not used by the running app:

| File | Reason |
|------|--------|
| `backups/` | Local backup ZIPs — not needed in repo |
| `attendance.csv` | Old flat-file remnant — app uses SQLite |
| `reset_attendance.py` | One-off script, functionality is in the web UI |
| `test_imports.py` | Dev-only import tester |
| `__pycache__/` | Python bytecode, auto-generated |
| `venv/` | Virtual environment, never commit this |

---

## 📦 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-...` | Flask session secret — **change in production** |

Set it in a `.env` file or export before running:
```bash
export SECRET_KEY="your-very-secret-key"
```

---

## 📤 Exporting Attendance

- **CSV** — Click "Download CSV" on the Attendance page
- **Excel** — Click "Download Excel" (requires `openpyxl`)
- **Defaulters CSV** — Export students below 75% attendance

---

## 📝 Notes

- The InsightFace `buffalo_l` model is downloaded automatically on first run (~300MB)
- Face encodings are stored as `.npy` files in `encodings/` — back these up if you retrain
- `dataset/{id}/name.txt` maps a student ID folder to a display name
- Recognition threshold defaults to `0.5` cosine similarity — adjust `RECOGNITION_THRESHOLD` in `app.py`