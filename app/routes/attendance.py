"""
Attendance Routes - Attendance management and reports
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.routes.auth import login_required
from app.models.database import get_db_connection
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/')
@login_required
def attendance():
    """Display attendance records"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Get recent attendance records
        cursor.execute("""
            SELECT a.id, s.name as student_name, s.roll_no,
                   sess.date, sub.subject_name, a.status, a.timestamp
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN sessions sess ON a.session_id = sess.id
            JOIN subjects sub ON sess.subject_id = sub.id
            ORDER BY sess.date DESC, a.timestamp DESC
            LIMIT 100
        """)
        attendance_records = cursor.fetchall()
        
        conn.close()
        
        return render_template('attendance.html', 
                             attendance_records=attendance_records,
                             session=session)
    
    except Exception as e:
        flash(f'Error loading attendance: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@attendance_bp.route('/report')
@login_required
def attendance_report():
    """Generate attendance report"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Get attendance statistics
        cursor.execute("""
            SELECT 
                s.name,
                s.roll_no,
                COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
                COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent_count,
                COUNT(*) as total_sessions,
                ROUND(CAST(COUNT(CASE WHEN a.status = 'present' THEN 1 END) AS FLOAT) / 
                      NULLIF(COUNT(*), 0) * 100, 2) as percentage
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id
            GROUP BY s.id
            ORDER BY s.name
        """)
        report_data = cursor.fetchall()
        
        conn.close()
        
        return render_template('attendance_report.html', 
                             report_data=report_data,
                             session=session)
    
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('attendance.attendance'))