"""
Subjects Routes - Subject management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.routes.auth import login_required
from app.models.database import get_db_connection

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route('/')
@login_required
def subjects_page():
    """Display all subjects"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, subject_name, subject_code, credits
            FROM subjects
            ORDER BY subject_name
        """)
        subjects_list = cursor.fetchall()
        
        conn.close()
        
        return render_template('subjects.html', subjects=subjects_list, session=session)
    
    except Exception as e:
        flash(f'Error loading subjects: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@subjects_bp.route('/add', methods=['POST'])
@login_required
def add_subject():
    """Add a new subject"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO subjects (subject_name, subject_code, credits)
            VALUES (?, ?, ?)
        """, (
            request.form.get('subject_name'),
            request.form.get('subject_code'),
            request.form.get('credits')
        ))
        
        conn.commit()
        conn.close()
        
        flash('Subject added successfully', 'success')
    except Exception as e:
        flash(f'Error adding subject: {str(e)}', 'error')
    
    return redirect(url_for('subjects.subjects_page'))