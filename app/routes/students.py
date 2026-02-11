"""
Students Routes - Student management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from app.routes.auth import login_required
from app.models.database import get_db_connection

students_bp = Blueprint('students', __name__)

@students_bp.route('/')
@login_required
def students():
    """Display all students"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, roll_no, email, phone, department, year
            FROM students
            ORDER BY name
        """)
        students_list = cursor.fetchall()
        
        conn.close()
        
        return render_template('students.html', students=students_list)
    
    except Exception as e:
        flash(f'Error loading students: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@students_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_student():
    """Add a new student"""
    if request.method == 'POST':
        try:
            conn = get_db_connection(current_app.config['DATABASE_PATH'])
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO students (name, roll_no, email, phone, department, year)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.form.get('name'),
                request.form.get('roll_no'),
                request.form.get('email'),
                request.form.get('phone'),
                request.form.get('department'),
                request.form.get('year')
            ))
            
            conn.commit()
            conn.close()
            
            flash('Student added successfully', 'success')
            return redirect(url_for('students.students'))
        
        except Exception as e:
            flash(f'Error adding student: {str(e)}', 'error')
    
    return render_template('add_student.html')