#!/usr/bin/env python3
"""
reset_attendance.py
Reset attendance database and encodings.
Use with caution - this will delete all data!
"""

import os
import sys
import json
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

BASE_DIR = Path(__file__).parent.absolute()
DB_PATH = BASE_DIR / "attendance.db"
DATASET_DIR = BASE_DIR / "dataset"
ENCODINGS_DIR = BASE_DIR / "encodings"
INDEX_FILE = ENCODINGS_DIR / "index.json"

def confirm_reset():
    """Get confirmation from user"""
    print("\n" + "="*60)
    print("⚠️  WARNING: RESET ATTENDANCE SYSTEM")
    print("="*60)
    print("This will delete:")
    print("  1. All attendance records")
    print("  2. All face encodings")
    print("  3. All student face images")
    print("  4. All sessions")
    print("\nThe following will be preserved:")
    print("  1. User accounts (admin, teachers, students)")
    print("  2. Subject list")
    print("  3. System configuration")
    
    response = input("\nType 'RESET' to confirm: ").strip()
    return response.upper() == "RESET"

def reset_database():
    """Reset database while preserving users and subjects"""
    import sqlite3
    from werkzeug.security import generate_password_hash
    
    if not DB_PATH.exists():
        print("❌ Database not found")
        return False
    
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Backup users and subjects
        print("📋 Backing up users...")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        print("📋 Backing up subjects...")
        cursor.execute("SELECT * FROM subjects")
        subjects = cursor.fetchall()
        
        # Drop and recreate tables
        print("🗑️  Dropping tables...")
        cursor.execute("DROP TABLE IF EXISTS attendance")
        cursor.execute("DROP TABLE IF EXISTS sessions")
        cursor.execute("DROP TABLE IF EXISTS students")
        
        # Recreate students table
        cursor.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT UNIQUE,
                name TEXT NOT NULL,
                department TEXT,
                face_count INTEGER DEFAULT 0,
                attendance_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Recreate sessions table
        cursor.execute("""
            CREATE TABLE sessions (
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
        """)
        
        # Recreate attendance table
        cursor.execute("""
            CREATE TABLE attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                status TEXT CHECK(status IN ('present','absent')) NOT NULL DEFAULT 'absent',
                marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL,
                UNIQUE(session_id, student_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Database reset successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return False

def reset_encodings():
    """Delete all face encodings"""
    try:
        if ENCODINGS_DIR.exists():
            print("🗑️  Deleting encodings...")
            for file in ENCODINGS_DIR.glob("*.npy"):
                file.unlink()
                print(f"   Deleted: {file.name}")
            
            if INDEX_FILE.exists():
                INDEX_FILE.unlink()
                print("   Deleted: index.json")
        
        print("✅ Encodings reset successfully")
        return True
    except Exception as e:
        print(f"❌ Error resetting encodings: {e}")
        return False

def reset_dataset():
    """Delete all student face images"""
    try:
        if DATASET_DIR.exists():
            print("🗑️  Deleting dataset...")
            for student_dir in DATASET_DIR.iterdir():
                if student_dir.is_dir():
                    shutil.rmtree(student_dir)
                    print(f"   Deleted: {student_dir.name}")
        
        print("✅ Dataset reset successfully")
        return True
    except Exception as e:
        print(f"❌ Error resetting dataset: {e}")
        return False

def main():
    """Main reset function"""
    print("\n" + "="*60)
    print("🔄 ATTENDANCE SYSTEM RESET TOOL")
    print("="*60)
    
    if not confirm_reset():
        print("\n❌ Reset cancelled")
        return False
    
    print("\n" + "="*60)
    print("🔄 STARTING RESET PROCESS")
    print("="*60)
    
    success = True
    
    # Reset database
    if not reset_database():
        success = False
    
    # Reset encodings
    if not reset_encodings():
        success = False
    
    # Reset dataset
    if not reset_dataset():
        success = False
    
    print("\n" + "="*60)
    if success:
        print("✅ RESET COMPLETED SUCCESSFULLY")
        print("\nNext steps:")
        print("  1. Add students using the Students page")
        print("  2. Upload face images for each student")
        print("  3. Generate face encodings")
        print("  4. Create sessions and start taking attendance")
    else:
        print("❌ RESET FAILED - Some operations may not have completed")
    
    print("="*60)
    return success

if __name__ == "__main__":
    main()