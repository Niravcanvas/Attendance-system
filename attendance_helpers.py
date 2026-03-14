"""
Helper functions for attendance operations
"""
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "attendance.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def mark_attendance(session_id, student_id, status='present'):
    """Mark attendance for a student in a session."""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT OR REPLACE INTO attendance (session_id, student_id, status)
            VALUES (?, ?, ?)
        """, (session_id, student_id, status))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error marking attendance: {e}")
        return False
    finally:
        conn.close()

def create_session(subject_id, teacher_id, date, start_time, end_time):
    """Create a new session and return its ID."""
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO sessions (subject_id, teacher_id, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (subject_id, teacher_id, date, start_time, end_time))
        
        session_id = cur.lastrowid
        conn.commit()
        return session_id
    except Exception as e:
        print(f"Error creating session: {e}")
        return None
    finally:
        conn.close()

def get_todays_attendance():
    """Get all attendance marked today."""
    conn = get_db()
    cur = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    cur.execute("""
        SELECT s.name, a.status, ss.date, ss.start_time, sub.subject_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN sessions ss ON a.session_id = ss.id
        JOIN subjects sub ON ss.subject_id = sub.id
        WHERE ss.date = ?
        ORDER BY ss.start_time DESC
    """, (today,))
    
    rows = cur.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_student_attendance_summary(student_id, start_date=None, end_date=None):
    """Get attendance summary for a student."""
    conn = get_db()
    cur = conn.cursor()
    
    query = """
        SELECT 
            COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
            COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent_count,
            COUNT(*) as total_sessions
        FROM attendance a
        JOIN sessions s ON a.session_id = s.id
        WHERE a.student_id = ?
    """
    params = [student_id]
    
    if start_date and end_date:
        query += " AND s.date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    cur.execute(query, params)
    result = cur.fetchone()
    conn.close()
    
    if result:
        total = result['total_sessions']
        percentage = (result['present_count'] / total * 100) if total > 0 else 0
        return {
            'present_count': result['present_count'],
            'absent_count': result['absent_count'],
            'total_sessions': total,
            'percentage': round(percentage, 1)
        }
    
    return None