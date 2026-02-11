"""
Sessions Routes - Class session management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.routes.auth import login_required
from app.models.database import get_db_connection
from datetime import datetime

sessions_bp = Blueprint('sessions', __name__)

@sessions_bp.route('/')
@login_required
def sessions_list():
    """Display all sessions"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.id, s.date, s.start_time, s.end_time,
                   sub.subject_name, u.full_name as teacher_name,
                   COUNT(a.id) as attendance_count
            FROM sessions s
            JOIN subjects sub ON s.subject_id = sub.id
            JOIN users u ON s.teacher_id = u.id
            LEFT JOIN attendance a ON s.id = a.session_id
            GROUP BY s.id
            ORDER BY s.date DESC, s.start_time DESC
        """)
        sessions_list = cursor.fetchall()
        
        conn.close()
        
        return render_template('sessions.html', sessions=sessions_list, session=session)
    
    except Exception as e:
        flash(f'Error loading sessions: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@sessions_bp.route('/create', methods=['POST'])
@login_required
def create_session():
    """Create a new session"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (date, start_time, end_time, subject_id, teacher_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            request.form.get('date'),
            request.form.get('start_time'),
            request.form.get('end_time'),
            request.form.get('subject_id'),
            request.form.get('teacher_id', session.get('user_id'))
        ))
        
        conn.commit()
        conn.close()
        
        flash('Session created successfully', 'success')
    except Exception as e:
        flash(f'Error creating session: {str(e)}', 'error')
    
    return redirect(url_for('sessions.sessions_list'))