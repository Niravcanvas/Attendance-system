"""
Dashboard Routes
"""
from flask import Blueprint, render_template, current_app
from datetime import datetime
from app.routes.auth import login_required
from app.models.database import get_db_connection

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/index')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard page"""
    conn = get_db_connection(current_app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    # Get statistics
    stats = {}
    
    # Total students
    cursor.execute("SELECT COUNT(*) as count FROM students")
    stats['total_students'] = cursor.fetchone()['count']
    
    # Today's date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Today's sessions
    cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE date = ?", (today,))
    stats['today_sessions'] = cursor.fetchone()['count']
    
    # Today's attendance
    cursor.execute("""
        SELECT COUNT(DISTINCT a.student_id) as count
        FROM attendance a
        JOIN sessions s ON a.session_id = s.id
        WHERE s.date = ? AND a.status = 'present'
    """, (today,))
    stats['today_attendance'] = cursor.fetchone()['count']
    
    # Total attendance records
    cursor.execute("SELECT COUNT(*) as count FROM attendance WHERE status = 'present'")
    stats['total_attendance'] = cursor.fetchone()['count']
    
    # Get top 5 students by attendance
    cursor.execute("""
        SELECT s.name, s.department,
               COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
               COUNT(*) as total_count,
               ROUND(COUNT(CASE WHEN a.status = 'present' THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
        HAVING total_count > 0
        ORDER BY percentage DESC
        LIMIT 5
    """)
    top_students = cursor.fetchall()
    
    # Get recent sessions
    cursor.execute("""
        SELECT s.id, s.date, s.start_time, s.end_time,
               sub.subject_name, u.full_name as teacher_name,
               COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count
        FROM sessions s
        JOIN subjects sub ON s.subject_id = sub.id
        JOIN users u ON s.teacher_id = u.id
        LEFT JOIN attendance a ON s.id = a.session_id
        GROUP BY s.id
        ORDER BY s.date DESC, s.start_time DESC
        LIMIT 5
    """)
    recent_sessions = cursor.fetchall()
    
    # Get all subjects for dropdown
    cursor.execute("SELECT id, subject_name FROM subjects ORDER BY subject_name")
    subjects = cursor.fetchall()
    
    # Get all teachers for dropdown
    cursor.execute("SELECT id, full_name FROM users WHERE role = 'teacher' ORDER BY full_name")
    teachers = cursor.fetchall()
    
    conn.close()
    
    # Check if encodings exist
    from pathlib import Path
    index_file = current_app.config['ENCODINGS_DIR'] / 'index.json'
    encodings_exist = index_file.exists() and index_file.stat().st_size > 0
    
    # Check InsightFace availability
    from app import get_face_service
    face_service = get_face_service()
    insightface_available = face_service and face_service.initialized
    
    return render_template('index.html',
                          stats=stats,
                          top_students=top_students,
                          recent_sessions=recent_sessions,
                          subjects=subjects,
                          teachers=teachers,
                          encodings_exist=encodings_exist,
                          insightface_available=insightface_available,
                          datetime=datetime)