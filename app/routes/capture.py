"""
Capture Routes - Face capture and recognition interface
"""
from flask import Blueprint, render_template, session, redirect, url_for, current_app
from app.routes.auth import login_required
from app.models.database import get_db_connection

capture_bp = Blueprint('capture', __name__)

@capture_bp.route('/capture')
@login_required
def capture_page():
    """Render the face capture page"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Get all students for the dropdown
        cursor.execute("SELECT id, name, roll_no FROM students ORDER BY name")
        students = cursor.fetchall()
        
        # Get all subjects
        cursor.execute("SELECT id, subject_name FROM subjects ORDER BY subject_name")
        subjects = cursor.fetchall()
        
        # Get all teachers
        cursor.execute("SELECT id, full_name FROM users WHERE role = 'teacher' ORDER BY full_name")
        teachers = cursor.fetchall()
        
        # Get student count
        cursor.execute("SELECT COUNT(*) as count FROM students")
        result = cursor.fetchone()
        student_count = result['count'] if result else 0
        
        conn.close()
        
        return render_template('capture.html',
                             students=students,
                             subjects=subjects,
                             teachers=teachers,
                             student_count=student_count,
                             session=session)
    
    except Exception as e:
        print(f"Error loading capture page: {e}")
        return redirect(url_for('dashboard.index'))