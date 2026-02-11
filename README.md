# AI Attendance System

An intelligent face recognition-based attendance system using InsightFace and Flask.

## Features

- Face recognition-based attendance marking
- Real-time camera capture
- Student and teacher management
- Attendance reports and analytics
- Session management
- Role-based access control (Admin, Teacher, Student)
- Attendance percentage tracking
- Export attendance to CSV

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Webcam (for live capture)
- 4GB RAM minimum (8GB recommended for better performance)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd Attendance-system
```

2. **Create a virtual environment**
```bash
python3 -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env and set your SECRET_KEY
```

5. **Initialize the database**
```bash
python scripts/init_db.py
```

6. **Run the application**
```bash
python run.py
```

7. **Access the application**
Open your browser and navigate to:
```
http://localhost:5000
```

> **Note:** If port 5000 is in use (common on macOS with AirPlay), the app will automatically try port 5001.

### Default Credentials

```
Admin:
Username: admin
Password: admin123

Teacher:
Username: teacher1
Password: teacher123

Student:
Username: student1
Password: student123
```

**Important:** Change default passwords after first login!

## Project Structure

```
Attendance-system/
├── app/                          # Application package
│   ├── __init__.py              # App factory
│   ├── config.py                # Configuration settings
│   ├── models/                  # Database models
│   │   ├── __init__.py
│   │   └── database.py
│   ├── routes/                  # Route blueprints
│   │   ├── __init__.py
│   │   ├── api.py              # API endpoints
│   │   ├── attendance.py       # Attendance routes
│   │   ├── auth.py             # Authentication
│   │   ├── dashboard.py        # Dashboard
│   │   ├── sessions.py         # Session management
│   │   ├── students.py         # Student management
│   │   └── subjects.py         # Subject management
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── face_recognition.py # Face recognition service
│   │   ├── file_management.py  # File operations
│   │   └── image_processing.py # Image processing
│   ├── static/                  # Static files
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       ├── camera.js
│   │       ├── classphoto.js
│   │       ├── dashboard.js
│   │       ├── students.js
│   │       ├── ui.js
│   │       └── webcam_capture.js
│   └── templates/               # HTML templates
│       ├── attendance.html
│       ├── base.html
│       ├── capture.html
│       ├── create_session.html
│       ├── index.html
│       ├── login.html
│       ├── realtime.html
│       ├── students.html
│       ├── subjects.html
│       └── users.html
├── data/                        # Data directory
│   ├── database/               # SQLite database
│   │   └── attendance.db
│   ├── dataset/                # Student face images
│   ├── encodings/              # Face embeddings (.npy files)
│   │   ├── index.json
│   │   ├── subjects.json
│   │   ├── teachers.json
│   │   └── *.npy              # Individual face encodings
│   └── uploads/                # Uploaded files
│       ├── faces/             # Captured face images
│       └── thumbs/            # Thumbnail images
├── logs/                        # Application logs
│   └── app.log
├── scripts/                     # Utility scripts
│   ├── init_db.py             # Database initialization
│   ├── encode_faces.py        # Face encoding script
│   └── cleanup.py             # Cleanup old files
├── tests/                       # Unit tests
├── venv/                        # Virtual environment
├── .env                         # Environment variables (not in git)
├── .env.example                # Example environment file
├── .gitignore                  # Git ignore rules
├── GUIDE.md                    # Development guide
├── README.md                   # This file
├── requirements.txt            # Python dependencies
└── run.py                      # Application entry point
```

## Usage

### Adding Students

1. Login as Admin or Teacher
2. Navigate to **Students** page
3. Click **Add Student**
4. Fill in student details
5. Upload face images (3-5 images recommended)
6. Click **Save**

### Encoding Faces

Before marking attendance, you need to encode face images:

**Option 1: Via Dashboard**
1. Go to **Dashboard**
2. Click **Encode Faces** button
3. Wait for encoding to complete

**Option 2: Via Command Line**
```bash
python scripts/encode_faces.py
```

### Marking Attendance

1. Login as Teacher
2. Go to **Capture** page
3. Select Subject and Session details
4. Click **Start Camera**
5. Capture class photo
6. Click **Recognize & Mark Attendance**

### Viewing Reports

1. Navigate to **Attendance** page
2. Use filters to select:
   - Date range
   - Subject
   - Teacher
3. View attendance statistics
4. Export to CSV if needed

## Configuration

### Environment Variables (.env)

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production

# Optional: Override default settings
# DATABASE_PATH=data/database/attendance.db
# RECOGNITION_THRESHOLD=0.5
# REVERIFY_THRESHOLD=0.6
```

### Config File (app/config.py)

Key settings you can modify:

- **Recognition Thresholds:** Adjust face matching sensitivity
- **File Upload Limits:** Change max file size
- **Session Duration:** Modify login session lifetime
- **Face Model:** Change InsightFace model (default: buffalo_l)

## Running Tests

```bash
# Run all tests
pytest tests/

# With coverage report
pytest --cov=app tests/

# Verbose output
pytest -v tests/
```

## Development

### Code Formatting
```bash
black app/
```

### Linting
```bash
flake8 app/
```

### Cleanup Old Files
```bash
python scripts/cleanup.py
```

### Database Reset
```bash
python scripts/init_db.py --reset
```

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - User login
- `GET /logout` - User logout

### Dashboard
- `GET /` - Dashboard home
- `GET /api/dashboard_stats` - Dashboard statistics

### Students
- `GET /students` - List students
- `POST /students/add` - Add student
- `POST /students/<id>/edit` - Edit student
- `DELETE /students/<id>` - Delete student
- `POST /students/<id>/upload-face` - Upload face image

### Subjects
- `GET /subjects` - List subjects
- `POST /subjects/add` - Add subject
- `POST /subjects/<id>/edit` - Edit subject
- `DELETE /subjects/<id>` - Delete subject

### Sessions
- `GET /sessions` - List sessions
- `POST /sessions/create` - Create session
- `GET /sessions/<id>` - View session details

### Attendance
- `GET /attendance` - View attendance records
- `POST /attendance/mark` - Mark attendance
- `GET /attendance/report` - Generate report
- `GET /download_attendance_report` - Export to CSV

### API
- `GET /api/health` - System health check
- `POST /api/detect` - Detect faces in image
- `POST /api/recognize` - Recognize faces and mark attendance

## Security

- Passwords are hashed using Werkzeug security
- Session-based authentication with secure cookies
- Role-based access control (RBAC)
- File upload validation and size limits
- SQL injection protection via SQLAlchemy ORM
- XSS protection via Jinja2 auto-escaping

**Recommended Additions:**
- CSRF protection (Flask-WTF)
- Rate limiting (Flask-Limiter)
- HTTPS in production

## Troubleshooting

### InsightFace Installation Issues

If you encounter issues installing InsightFace:

**On Windows:**
```bash
pip install insightface --no-deps
pip install onnxruntime numpy opencv-python
```

**On macOS:**
```bash
brew install cmake
pip install insightface
```

**On Linux:**
```bash
sudo apt-get install cmake
pip install insightface
```

### Port 5000 Already in Use

**On macOS:**
Port 5000 is often used by AirPlay Receiver.

**Option 1:** Disable AirPlay Receiver
- System Preferences → General → AirDrop & Handoff
- Uncheck "AirPlay Receiver"

**Option 2:** Kill the process
```bash
lsof -ti:5000 | xargs kill -9
```

**Option 3:** The app automatically tries port 5001 if 5000 is busy

### Camera Not Working

1. **Check browser permissions** - Allow camera access
2. **Ensure camera is not in use** by another application
3. **Try a different browser** (Chrome recommended)
4. **Check HTTPS** - Some browsers require HTTPS for camera access

### Face Recognition Not Working

1. **Encode faces first**
   ```bash
   python scripts/encode_faces.py
   ```

2. **Check image quality**
   - Good lighting
   - Face clearly visible
   - No obstructions

3. **Adjust thresholds** in `app/config.py`:
   ```python
   RECOGNITION_THRESHOLD = 0.5  # Lower = more lenient
   REVERIFY_THRESHOLD = 0.6
   ```

### Database Errors

**Reset the database:**
```bash
python scripts/init_db.py --reset
```

**Check database file permissions:**
```bash
chmod 664 data/database/attendance.db
```

### OpenSSL Warning

If you see the urllib3 OpenSSL warning on macOS:
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
```

This is a warning, not an error. The app will still work. To fix:
```bash
brew install openssl
pip install --upgrade urllib3
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- InsightFace for face recognition models
- Flask for the web framework
- OpenCV for image processing
- SQLAlchemy for database ORM

## Support

For issues and questions:
- Open an issue on GitHub
- Check the GUIDE.md for development details
- Review logs in `logs/app.log`

---