"""
Users Routes - User management (Admin only)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.routes.auth import login_required
from app.models.database import get_db_connection
import hashlib

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
@login_required
def users_page():
    """Display all users (admin only)"""
    if session.get('user_role') != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, full_name, email, role, department
            FROM users
            ORDER BY full_name
        """)
        users_list = cursor.fetchall()
        
        conn.close()
        
        return render_template('users.html', users=users_list, session=session)
    
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@users_bp.route('/add', methods=['POST'])
@login_required
def add_user():
    """Add a new user (admin only)"""
    if session.get('user_role') != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Hash password
        password = request.form.get('password')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, department)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form.get('username'),
            password_hash,
            request.form.get('full_name'),
            request.form.get('email'),
            request.form.get('role'),
            request.form.get('department')
        ))
        
        conn.commit()
        conn.close()
        
        flash('User added successfully', 'success')
    except Exception as e:
        flash(f'Error adding user: {str(e)}', 'error')
    
    return redirect(url_for('users.users_page'))