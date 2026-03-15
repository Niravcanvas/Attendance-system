# AI Attendance System

A face-recognition-based attendance system built with Flask, InsightFace, and MongoDB. Capture a photo of a classroom and the system automatically detects faces, matches them against enrolled students, and records attendance — all without manual input.

---

## Features

- **Automated Face Recognition** — Detects and recognizes multiple faces in a single classroom photo using InsightFace (`buffalo_l` model)
- **Role-Based Access Control** — Separate dashboards and permissions for Admin, Teacher, and Student roles
- **Session Management** — Create and manage class sessions per subject and teacher
- **Attendance Reports** — Filter and export attendance records to CSV with date, subject, and teacher filters
- **Defaulters Report** — Automatically identifies students below 75% attendance threshold
- **Manual Override** — Mark individual students present manually when needed
- **Background Encoding** — Face encoding runs in a background thread without blocking the UI

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask |
| Database | MongoDB (PyMongo) |
| Face Recognition | InsightFace (`buffalo_l`), ONNX Runtime |
| Image Processing | OpenCV, Pillow |
| Frontend | Jinja2, HTML, CSS, JavaScript |
| Environment | python-dotenv |

---

## Project Structure

```
Attendance System/
├── app.py                  # Main Flask application — all routes and logic
├── db.py                   # MongoDB connection, index creation
├── init_db.py              # Seeds default users and subjects on first run
├── config.py               # Environment-aware configuration class
├── requirements.txt
├── .env                    # Local environment variables (never commit)
├── .env.example            # Template for environment variables
├── README.md
├── .gitignore
├── dataset/                # Student face images, organised by student ID
│   └── {student_id}/
│       ├── name.txt        # Student display name
│       └── *.jpg
├── encodings/              # Face embeddings
│   ├── index.json          # Maps student IDs to names and embedding files
│   └── {student_id}.npy   # Numpy embedding vectors
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
├── uploads/                # Captured and annotated images (auto-created)
└── logs/                   # Application logs and timeline (auto-created)
```

---

## Requirements

- Python 3.10 or higher
- MongoDB running locally or a remote connection string
- CMake and a C++ compiler (required by InsightFace)
  - macOS: `brew install cmake`
  - Ubuntu/Debian: `sudo apt install cmake build-essential`

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/attendance-system.git
cd "attendance-system"
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```
SECRET_KEY=your-random-secret-key
MONGO_URI=mongodb://localhost:27017
MONGO_DB=attendance_system
PORT=5001
```

Generate a secure secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Start MongoDB

```bash
brew services start mongodb-community   # macOS
sudo systemctl start mongod             # Linux
```

### 6. Initialise the database

```bash
python init_db.py
```

This creates indexes and seeds the default admin, teacher, and student accounts.

### 7. Run the application

```bash
python app.py
```

The server starts at `http://localhost:5001`

---

## Default Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Teacher | `teacher1` | `teacher123` |
| Student | `student1` | `student123` |

Change these immediately after the first login in production.

---

## How Attendance Works

1. **Add Students** — Go to the Students page, add a student with a username and password, and upload face photos
2. **Encode Faces** — Click "Encode Faces" on the dashboard to generate face embeddings (runs in background)
3. **Create a Session** — Select a subject, teacher, date, and time slot
4. **Capture and Recognize** — On the Capture page, take or upload a class photo and click Recognize
5. **Review Results** — The Attendance page shows per-session records, per-student summaries, and defaulters

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-...` | Flask session secret — must be changed in production |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `attendance_system` | MongoDB database name |
| `RECOGNITION_THRESHOLD` | `0.5` | Cosine similarity threshold for face matching (0.0–1.0) |
| `INSIGHTFACE_MODEL` | `buffalo_l` | InsightFace model name |
| `USE_CUDA` | `false` | Set to `true` if an NVIDIA GPU is available |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `5001` | Server port |
| `FLASK_ENV` | `development` | `development` or `production` |

---

## Exporting Attendance

- **CSV** — Available on the Attendance page with subject, teacher, and date filters applied
- **Defaulters CSV** — Lists all students below 75% attendance for the selected period

---

## Notes

- The `buffalo_l` InsightFace model (~300MB) is downloaded automatically on first run and cached at `~/.insightface/models/`
- Face embeddings are stored as `.npy` files in `encodings/` — back these up before re-encoding
- `dataset/{id}/name.txt` maps a student folder to a display name; this file must exist for encoding to work correctly
- The recognition threshold defaults to `0.5` — increase it for stricter matching, decrease it if legitimate students are not being recognised
- `uploads/` and `logs/` are created automatically and are excluded from version control

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a pull request