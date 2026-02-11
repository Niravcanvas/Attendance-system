"""
API Routes - All API endpoints for the application
"""
import os
import io
import csv
import json
import base64
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, session, send_file, Response
from werkzeug.utils import secure_filename
from app.routes.auth import login_required, role_required
from app.models.database import get_db_connection
from app import get_face_service
import humanize

api_bp = Blueprint('api', __name__)

# Helper functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_thumbnail(image_path, max_size=320):
    """Create thumbnail for an image"""
    try:
        thumb_dir = current_app.config['UPLOADS_DIR'] / 'thumbs'
        thumb_dir.mkdir(exist_ok=True)
        
        img = Image.open(str(image_path)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        thumb_name = f"thumb_{image_path.name}"
        thumb_path = thumb_dir / thumb_name
        img.save(str(thumb_path), "JPEG", quality=85)
        
        return f"uploads/thumbs/{thumb_name}"
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None

# ==================== HEALTH CHECK ====================
@api_bp.route('/health_check')
def health_check():
    """Health check endpoint"""
    checks = {
        'database': False,
        'face_recognition': False,
        'directories': False
    }
    
    # Check database
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        conn.execute('SELECT 1')
        conn.close()
        checks['database'] = True
    except:
        pass
    
    # Check face recognition
    face_service = get_face_service()
    checks['face_recognition'] = face_service and face_service.initialized
    
    # Check directories
    directories_exist = all([
        current_app.config['DATASET_DIR'].exists(),
        current_app.config['ENCODINGS_DIR'].exists(),
        current_app.config['UPLOADS_DIR'].exists()
    ])
    checks['directories'] = directories_exist
    
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    
    return jsonify({
        'status': status,
        'checks': checks,
        'timestamp': datetime.now().isoformat()
    })

# ==================== UPLOAD PHOTO ====================
@api_bp.route('/upload_photo', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def upload_photo():
    """Upload a photo (class or student)"""
    try:
        uploads_dir = current_app.config['UPLOADS_DIR']
        
        # Check if image data is provided
        if 'image' not in request.files and 'imageData' not in request.form:
            return jsonify({'success': False, 'error': 'No image provided'}), 400
        
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"class_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                filepath = uploads_dir / filename
                file.save(str(filepath))
                
                # Create thumbnail
                save_thumbnail(filepath)
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'message': 'Photo uploaded successfully'
                })
        
        # Handle base64 image data
        elif 'imageData' in request.form:
            image_data = request.form['imageData']
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes)).convert('RGB')
            
            filename = f"class_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = uploads_dir / filename
            image.save(str(filepath), 'JPEG', quality=90)
            
            # Create thumbnail
            save_thumbnail(filepath)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': 'Photo captured successfully'
            })
        
        return jsonify({'success': False, 'error': 'Invalid image format'}), 400
    
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== RECOGNIZE FACES ====================
@api_bp.route('/recognize', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def recognize():
    """Recognize faces in the latest photo and mark attendance"""
    try:
        uploads_dir = current_app.config['UPLOADS_DIR']
        
        # Get the latest photo
        photos = list(uploads_dir.glob('class_*.jpg'))
        if not photos:
            return jsonify({'success': False, 'error': 'No photos found'}), 400
        
        latest_photo = max(photos, key=lambda x: x.stat().st_ctime)
        
        # Get subject and teacher info
        subject_id = request.form.get('subject_id')
        teacher_id = request.form.get('teacher_id', session.get('user_id'))
        threshold = float(request.form.get('threshold', 0.5))
        
        if not subject_id:
            return jsonify({'success': False, 'error': 'Subject is required'}), 400
        
        # Get face recognition service
        face_service = get_face_service()
        if not face_service or not face_service.initialized:
            return jsonify({'success': False, 'error': 'Face recognition not initialized'}), 500
        
        # Recognize faces
        result = face_service.recognize_faces_in_image(str(latest_photo), threshold=threshold)
        
        if not result.get('success'):
            return jsonify(result), 400
        
        # Create session and mark attendance
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        start_time = datetime.now().strftime("%H:%M")
        end_time = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
        
        # Create session
        cursor.execute("""
            INSERT INTO sessions (subject_id, teacher_id, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (subject_id, teacher_id, today, start_time, end_time))
        session_id = cursor.lastrowid
        
        # Mark attendance for recognized students
        marked_students = []
        for recognition in result.get('recognitions', []):
            if recognition['name'] != 'Unknown':
                # Get student
                cursor.execute("SELECT id FROM students WHERE name = ?", (recognition['name'],))
                student = cursor.fetchone()
                
                if student:
                    student_id = student['id']
                    
                    # Mark as present
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance (session_id, student_id, status, confidence)
                        VALUES (?, ?, 'present', ?)
                    """, (session_id, student_id, recognition['confidence']))
                    
                    marked_students.append(recognition['name'])
        
        # Mark all other students as absent
        cursor.execute("SELECT id FROM students")
        all_students = cursor.fetchall()
        
        for student in all_students:
            cursor.execute("""
                INSERT OR IGNORE INTO attendance (session_id, student_id, status)
                VALUES (?, ?, 'absent')
            """, (session_id, student['id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked for {len(marked_students)} students',
            'faces_found': result.get('faces_found', 0),
            'recognized': len(marked_students),
            'annotated_image': result.get('annotated_image'),
            'marked_students': marked_students
        })
    
    except Exception as e:
        print(f"Recognition error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENCODE FACES ====================
@api_bp.route('/encode', methods=['POST'])
@login_required
@role_required('admin')
def encode_faces():
    """Encode all student faces in dataset"""
    try:
        face_service = get_face_service()
        if not face_service or not face_service.initialized:
            return jsonify({
                'success': False,
                'error': 'Face recognition not initialized'
            }), 500
        
        dataset_dir = current_app.config['DATASET_DIR']
        
        if not dataset_dir.exists():
            return jsonify({
                'success': False,
                'error': 'Dataset directory does not exist'
            }), 400
        
        # Get all student directories
        student_dirs = [d for d in dataset_dir.iterdir() if d.is_dir()]
        
        if not student_dirs:
            return jsonify({
                'success': False,
                'error': 'No students found in dataset directory'
            }), 400
        
        # Encode faces for each student
        total_embeddings = 0
        processed_students = 0
        
        for student_dir in student_dirs:
            student_name = student_dir.name
            
            # Get all image files
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                image_files.extend(list(student_dir.glob(ext)))
            
            if not image_files:
                continue
            
            # Process images
            embeddings = []
            for image_path in image_files:
                try:
                    # Load image
                    img = cv2.imread(str(image_path))
                    if img is None:
                        continue
                    
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    
                    # Detect and extract embedding
                    faces = face_service.detect_faces(img_rgb)
                    if faces and len(faces) > 0:
                        face = faces[0]
                        if 'embedding' in face and face['embedding'] is not None:
                            embeddings.append(face['embedding'])
                            total_embeddings += 1
                
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
                    continue
            
            # Save embeddings
            if embeddings:
                embeddings_array = np.array(embeddings)
                face_service.save_student_embeddings(student_name, embeddings_array)
                processed_students += 1
        
        return jsonify({
            'success': True,
            'message': f'Encoded {total_embeddings} faces for {processed_students} students',
            'total_embeddings': total_embeddings,
            'processed_students': processed_students
        })
    
    except Exception as e:
        print(f"Encoding error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== RECENT CAPTURES ====================
@api_bp.route('/recent_captures')
@login_required
def recent_captures():
    """Get recent captures from uploads directory"""
    try:
        uploads_dir = current_app.config['UPLOADS_DIR']
        thumb_dir = uploads_dir / 'thumbs'
        
        # Get all image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_files.extend(list(uploads_dir.glob(ext)))
        
        # Sort by modification time (newest first)
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Get recent files (max 12)
        recent = []
        for file in image_files[:12]:
            stat = file.stat()
            timestamp = datetime.fromtimestamp(stat.st_mtime)
            
            # Check if thumbnail exists
            thumb_path = thumb_dir / f"thumb_{file.name}"
            thumbnail_url = f'/uploads/thumbs/thumb_{file.name}' if thumb_path.exists() else f'/uploads/{file.name}'
            
            # Classify type
            capture_type = "class"
            if file.name.startswith('annotated_'):
                capture_type = "annotated"
            elif file.name.startswith('student_'):
                capture_type = "student"
            
            recent.append({
                'id': file.name,
                'name': file.stem[:20] + ('...' if len(file.stem) > 20 else ''),
                'filename': file.name,
                'url': f'/uploads/{file.name}',
                'thumbnail': thumbnail_url,
                'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'time': humanize.naturaltime(timestamp),
                'size': humanize.naturalsize(stat.st_size),
                'type': capture_type
            })
        
        return jsonify({
            'success': True,
            'captures': recent
        })
    
    except Exception as e:
        print(f"Error loading recent captures: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'captures': []
        })

# ==================== DELETE CAPTURE ====================
@api_bp.route('/delete_capture/<filename>', methods=['DELETE'])
@login_required
@role_required('admin', 'teacher')
def delete_capture(filename):
    """Delete a capture file"""
    try:
        uploads_dir = current_app.config['UPLOADS_DIR']
        thumb_dir = uploads_dir / 'thumbs'
        
        safe_filename = secure_filename(filename)
        
        # Delete main file
        file_path = uploads_dir / safe_filename
        if file_path.exists():
            file_path.unlink()
        
        # Delete thumbnail
        thumb_path = thumb_dir / f"thumb_{safe_filename}"
        if thumb_path.exists():
            thumb_path.unlink()
        
        return jsonify({
            'success': True,
            'message': 'Capture deleted successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== CAPTURE STATISTICS ====================
@api_bp.route('/capture_statistics')
@login_required
def capture_statistics():
    """Get capture statistics"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # Count total face images
        cursor.execute("SELECT SUM(face_count) as total_faces FROM students")
        result = cursor.fetchone()
        total_faces = result['total_faces'] if result and result['total_faces'] else 0
        
        # Count today's captures
        today = datetime.now().strftime("%Y-%m-%d")
        uploads_dir = current_app.config['UPLOADS_DIR']
        
        image_files = list(uploads_dir.glob('*.jpg')) + list(uploads_dir.glob('*.png'))
        today_captures = sum(1 for f in image_files 
                           if datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d") == today)
        
        # Calculate storage
        storage_used = sum(f.stat().st_size for f in uploads_dir.rglob('*') if f.is_file())
        
        # Check encodings
        index_file = current_app.config['ENCODINGS_DIR'] / 'index.json'
        encodings_ready = index_file.exists() and index_file.stat().st_size > 0
        
        # Check recognition
        face_service = get_face_service()
        recognition_ready = face_service and face_service.initialized
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_faces': total_faces,
            'today_captures': today_captures,
            'storage_used': humanize.naturalsize(storage_used),
            'encodings_ready': encodings_ready,
            'recognition_ready': recognition_ready
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== CAPTURE STUDENT ====================
@api_bp.route('/capture_student', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def capture_student():
    """Capture and save face for a specific student"""
    try:
        if 'image' not in request.files or 'student_id' not in request.form:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        
        student_id = request.form['student_id']
        file = request.files['image']
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Get student
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        student_name = student['name']
        
        # Create student directory
        dataset_dir = current_app.config['DATASET_DIR']
        student_dir = dataset_dir / secure_filename(student_name)
        student_dir.mkdir(exist_ok=True)
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{secure_filename(student_name)}_{timestamp}.jpg"
        filepath = student_dir / filename
        file.save(str(filepath))
        
        # Also save to uploads
        uploads_dir = current_app.config['UPLOADS_DIR']
        upload_filename = f"student_{student_id}_{timestamp}.jpg"
        upload_path = uploads_dir / upload_filename
        
        # Copy the file
        with open(filepath, 'rb') as src:
            with open(upload_path, 'wb') as dst:
                dst.write(src.read())
        
        # Create thumbnail
        save_thumbnail(upload_path)
        
        # Update face count
        cursor.execute("""
            UPDATE students 
            SET face_count = COALESCE(face_count, 0) + 1 
            WHERE id = ?
        """, (student_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Face captured successfully',
            'student_name': student_name,
            'filepath': str(filepath)
        })
    
    except Exception as e:
        print(f"Capture student error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== UPLOAD FACES ====================
@api_bp.route('/upload_faces', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def upload_faces():
    """Upload multiple face images"""
    try:
        if 'images' not in request.files:
            return jsonify({'success': False, 'error': 'No images provided'}), 400
        
        files = request.files.getlist('images')
        uploaded_count = 0
        uploads_dir = current_app.config['UPLOADS_DIR']
        
        for file in files:
            if file and allowed_file(file.filename):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = secure_filename(f"upload_{timestamp}_{file.filename}")
                filepath = uploads_dir / filename
                file.save(str(filepath))
                
                # Create thumbnail
                save_thumbnail(filepath)
                uploaded_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Uploaded {uploaded_count} image(s)',
            'uploaded': uploaded_count
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== DASHBOARD STATS ====================
@api_bp.route('/dashboard_stats')
@login_required
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
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
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})