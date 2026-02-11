"""
Main Routes - Non-API routes that handle form submissions
These routes are called directly from forms, not AJAX
"""
from flask import Blueprint, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app.routes.auth import login_required, role_required
from app.models.database import get_db_connection
from app import get_face_service
from PIL import Image
from io import BytesIO
import base64

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/upload_photo', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def upload_photo():
    """Upload a photo (non-API version for form submissions)"""
    try:
        uploads_dir = current_app.config['UPLOADS_DIR']
        
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"class_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                filepath = uploads_dir / filename
                file.save(str(filepath))
                flash('Photo uploaded successfully', 'success')
                return redirect(url_for('capture.capture_page'))
        
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
            flash('Photo captured successfully', 'success')
            return redirect(url_for('capture.capture_page'))
        
        flash('No image provided', 'error')
        return redirect(url_for('capture.capture_page'))
    
    except Exception as e:
        flash(f'Error uploading photo: {str(e)}', 'error')
        return redirect(url_for('capture.capture_page'))

@main_bp.route('/recognize', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def recognize():
    """Recognize faces and mark attendance (non-API version)"""
    try:
        uploads_dir = current_app.config['UPLOADS_DIR']
        
        # Get the latest photo
        photos = list(uploads_dir.glob('class_*.jpg'))
        if not photos:
            flash('No photos found. Please capture a photo first.', 'error')
            return redirect(url_for('capture.capture_page'))
        
        latest_photo = max(photos, key=lambda x: x.stat().st_ctime)
        
        # Get form data
        subject_id = request.form.get('subject_id')
        teacher_id = request.form.get('teacher_id', session.get('user_id'))
        threshold = float(request.form.get('threshold', 0.5))
        
        if not subject_id:
            flash('Please select a subject', 'error')
            return redirect(url_for('capture.capture_page'))
        
        # Get face recognition service
        face_service = get_face_service()
        if not face_service or not face_service.initialized:
            flash('Face recognition service not available', 'error')
            return redirect(url_for('capture.capture_page'))
        
        # Recognize faces
        result = face_service.recognize_faces_in_image(str(latest_photo), threshold=threshold)
        
        if not result.get('success'):
            flash(f'Recognition failed: {result.get("error", "Unknown error")}', 'error')
            return redirect(url_for('capture.capture_page'))
        
        # Create session
        conn = get_db_connection(current_app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        start_time = datetime.now().strftime("%H:%M")
        end_time = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
        
        cursor.execute("""
            INSERT INTO sessions (subject_id, teacher_id, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (subject_id, teacher_id, today, start_time, end_time))
        session_id = cursor.lastrowid
        
        # Mark attendance
        marked_students = []
        for recognition in result.get('recognitions', []):
            if recognition['name'] != 'Unknown':
                cursor.execute("SELECT id FROM students WHERE name = ?", (recognition['name'],))
                student = cursor.fetchone()
                
                if student:
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance (session_id, student_id, status, confidence)
                        VALUES (?, ?, 'present', ?)
                    """, (session_id, student['id'], recognition['confidence']))
                    marked_students.append(recognition['name'])
        
        # Mark others as absent
        cursor.execute("SELECT id FROM students")
        all_students = cursor.fetchall()
        
        for student in all_students:
            cursor.execute("""
                INSERT OR IGNORE INTO attendance (session_id, student_id, status)
                VALUES (?, ?, 'absent')
            """, (session_id, student['id']))
        
        conn.commit()
        conn.close()
        
        flash(f'✅ Attendance marked! Recognized {len(marked_students)} of {result.get("faces_found", 0)} faces', 'success')
        return redirect(url_for('attendance.attendance'))
    
    except Exception as e:
        flash(f'Error during recognition: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('capture.capture_page'))

@main_bp.route('/encode', methods=['POST'])
@login_required
@role_required('admin')
def encode():
    """Encode all student faces"""
    try:
        face_service = get_face_service()
        if not face_service or not face_service.initialized:
            flash('Face recognition service not available', 'error')
            return redirect(url_for('dashboard.index'))
        
        dataset_dir = current_app.config['DATASET_DIR']
        if not dataset_dir.exists():
            flash('Dataset directory does not exist', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Get student directories
        student_dirs = [d for d in dataset_dir.iterdir() if d.is_dir()]
        
        if not student_dirs:
            flash('No students found in dataset directory', 'error')
            return redirect(url_for('dashboard.index'))
        
        # Encode faces
        total = 0
        processed = 0
        
        for student_dir in student_dirs:
            import cv2
            import numpy as np
            
            student_name = student_dir.name
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                image_files.extend(list(student_dir.glob(ext)))
            
            if not image_files:
                continue
            
            embeddings = []
            for image_path in image_files:
                try:
                    img = cv2.imread(str(image_path))
                    if img is None:
                        continue
                    
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    faces = face_service.detect_faces(img_rgb)
                    
                    if faces and len(faces) > 0:
                        face = faces[0]
                        if 'embedding' in face and face['embedding'] is not None:
                            embeddings.append(face['embedding'])
                            total += 1
                
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
                    continue
            
            if embeddings:
                embeddings_array = np.array(embeddings)
                face_service.save_student_embeddings(student_name, embeddings_array)
                processed += 1
        
        flash(f'✅ Successfully encoded {total} faces for {processed} students', 'success')
        return redirect(url_for('dashboard.index'))
    
    except Exception as e:
        flash(f'Error encoding faces: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('dashboard.index'))