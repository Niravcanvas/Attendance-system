"""
Database module for managing SQLite connections and operations
"""
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash


def get_db_connection(db_path):
    """Get database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(db_path):
    """Initialize database with all tables"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT CHECK(role IN ('admin', 'teacher', 'student')) NOT NULL DEFAULT 'student',
        full_name TEXT,
        department TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Subjects table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL,
        department TEXT NOT NULL DEFAULT 'General',
        teacher_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    )
    ''')
    
    # Students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT UNIQUE,
        name TEXT NOT NULL,
        department TEXT,
        face_count INTEGER DEFAULT 0,
        attendance_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        teacher_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (subject_id) REFERENCES subjects(id),
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    )
    ''')
    
    # Attendance table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT CHECK(status IN ('present', 'absent')) NOT NULL DEFAULT 'absent',
        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        confidence REAL,
        UNIQUE(session_id, student_id),
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    ''')
    
    # Check if default users exist
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] == 0:
        # Create default users
        default_users = [
            ('admin', generate_password_hash('admin123'), 'admin', 
             'System Administrator', 'Administration', 'admin@example.com'),
            ('teacher1', generate_password_hash('teacher123'), 'teacher', 
             'John Doe', 'Computer Science', 'teacher1@example.com'),
            ('student1', generate_password_hash('student123'), 'student', 
             'Alice Smith', 'Computer Science', 'student1@example.com')
        ]
        
        for username, pwd_hash, role, full_name, dept, email in default_users:
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, full_name, department, email) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, pwd_hash, role, full_name, dept, email)
                )
            except sqlite3.IntegrityError:
                pass
    
    # Add default subject
    cursor.execute("SELECT COUNT(*) FROM subjects WHERE subject_name = 'General'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO subjects (subject_name, department) VALUES (?, ?)", 
                      ('General', 'General'))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")


def update_student_statistics(db_path, encodings_index_file):
    """Update student face_count and attendance_count"""
    import json
    
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Update face counts from embeddings index
        if Path(encodings_index_file).exists():
            with open(encodings_index_file, 'r') as f:
                index = json.load(f)
            
            for student_name in index.keys():
                cursor.execute(
                    "UPDATE students SET face_count = COALESCE(face_count, 0) + 1 WHERE name = ?",
                    (student_name,)
                )
        
        # Update attendance counts
        cursor.execute("""
            UPDATE students 
            SET attendance_count = (
                SELECT COUNT(*) 
                FROM attendance a 
                WHERE a.student_id = students.id AND a.status = 'present'
            )
        """)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating statistics: {e}")