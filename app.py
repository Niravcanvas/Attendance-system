# app.py — AI Attendance System (MongoDB / PyMongo edition)

import os
from dotenv import load_dotenv
load_dotenv()

import io
import csv
import json
import base64
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from io import BytesIO

from bson import ObjectId
from bson.errors import InvalidId

# Optional imports with fallbacks
try:
    import humanize
    HUMANIZE_AVAILABLE = True
except ImportError:
    HUMANIZE_AVAILABLE = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

import numpy as np
import cv2
from PIL import Image, ImageOps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, Response, session, send_from_directory
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db, init_indexes, ping as db_ping

# ==================== CONFIGURATION ====================
BASE_DIR      = Path(__file__).parent.absolute()
DATASET_DIR   = BASE_DIR / "dataset"
ENCODINGS_DIR = BASE_DIR / "encodings"
UPLOADS_DIR   = BASE_DIR / "uploads"
FACES_DIR     = UPLOADS_DIR / "faces"
THUMB_DIR     = UPLOADS_DIR / "thumbs"
LOGS_DIR      = BASE_DIR / "logs"

for _d in [DATASET_DIR, ENCODINGS_DIR, UPLOADS_DIR, FACES_DIR, THUMB_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

INDEX_FILE    = ENCODINGS_DIR / "index.json"
TIMELINE_FILE = BASE_DIR / "timeline.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "PNG", "JPG", "JPEG"}

RECOGNITION_THRESHOLD = float(os.environ.get("RECOGNITION_THRESHOLD", 0.5))

# ==================== INSIGHTFACE ====================
try:
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

insightface_app = None
face_model      = None

def init_insightface():
    global insightface_app, face_model
    if not INSIGHTFACE_AVAILABLE:
        return False
    try:
        insightface_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        insightface_app.prepare(ctx_id=0, det_size=(640, 640))
        face_model = get_model("buffalo_l", download=True)
        face_model.prepare(ctx_id=0)
        return True
    except Exception as e:
        print(f"❌ InsightFace init failed: {e}")
        return False

# ==================== FLASK APP ====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_FOLDER"]      = str(UPLOADS_DIR)

@app.template_filter("js_escape")
def js_escape_filter(value):
    return json.dumps(str(value))[1:-1] if value else ""

@app.context_processor
def inject_now():
    return {"now": datetime.now(), "timedelta": timedelta}

# ==================== HELPERS ====================

def oid(value):
    """Safely cast a string to ObjectId; return None on failure."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {e.lower() for e in ALLOWED_EXTENSIONS}


def save_thumbnail(image_path, max_size=320):
    try:
        img = Image.open(str(image_path)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        thumb_name = f"thumb_{image_path.name}"
        thumb_path = THUMB_DIR / thumb_name
        img.save(str(thumb_path), "JPEG", quality=85)
        return f"uploads/thumbs/{thumb_name}"
    except Exception:
        return None


def save_file_copy(file_storage, dest_path):
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    file_storage.save(str(dest_path))


def fmt_created_at(doc):
    """Return a safe created_at string from a MongoDB document."""
    val = doc.get("created_at")
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str) and len(val) >= 10:
        return val[:10]
    return "N/A"


def append_to_timeline(photo_name, marked_count, total_faces, subject="", teacher=""):
    try:
        timeline = []
        if TIMELINE_FILE.exists():
            with open(TIMELINE_FILE) as f:
                timeline = json.load(f)
        timeline.insert(0, {
            "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "photo":       photo_name,
            "marked":      marked_count,
            "faces_found": total_faces,
            "subject":     subject,
            "teacher":     teacher,
        })
        timeline = timeline[:100]
        with open(TIMELINE_FILE, "w") as f:
            json.dump(timeline, f, indent=2)
    except Exception as e:
        print(f"Timeline error: {e}")

# ==================== EMBEDDINGS CACHE ====================
_embeddings_cache      = None
_embeddings_cache_lock = threading.Lock()


def load_all_embeddings(force_reload=False):
    global _embeddings_cache
    with _embeddings_cache_lock:
        if _embeddings_cache is not None and not force_reload:
            return _embeddings_cache
        if not INDEX_FILE.exists():
            _embeddings_cache = ([], np.zeros((0, 512), dtype=np.float32))
            return _embeddings_cache
        try:
            with open(INDEX_FILE) as f:
                index = json.load(f)
            all_names, all_embeddings = [], []
            for key, value in index.items():
                student_name = value["name"] if isinstance(value, dict) else key
                emb_filename = value["file"] if isinstance(value, dict) else value
                emb_path = ENCODINGS_DIR / emb_filename
                if emb_path.exists():
                    embeddings = np.load(str(emb_path))
                    if embeddings.ndim == 1:
                        embeddings = embeddings.reshape(1, -1)
                    all_names.extend([student_name] * embeddings.shape[0])
                    all_embeddings.append(embeddings)
            stacked = np.vstack(all_embeddings) if all_embeddings else np.zeros((0, 512), dtype=np.float32)
            _embeddings_cache = (all_names, stacked)
        except Exception as e:
            print(f"Embeddings load error: {e}")
            _embeddings_cache = ([], np.zeros((0, 512), dtype=np.float32))
        return _embeddings_cache


def invalidate_embeddings_cache():
    global _embeddings_cache
    with _embeddings_cache_lock:
        _embeddings_cache = None

# ==================== INSIGHTFACE FUNCTIONS ====================

def detect_faces(image_array):
    if not insightface_app:
        return []
    try:
        if len(image_array.shape) == 2:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
        elif image_array.shape[2] == 4:
            image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
        faces = insightface_app.get(image_array)
        return [{
            "bbox":      face.bbox.astype(int).tolist(),
            "landmarks": face.kps.tolist() if hasattr(face, "kps") and len(face.kps) else [],
            "det_score": float(face.det_score),
            "embedding": face.normed_embedding.tolist() if hasattr(face, "normed_embedding") else None,
        } for face in faces]
    except Exception as e:
        print(f"detect_faces error: {e}")
        return []


def extract_embedding(image_array, bbox):
    if not face_model:
        return None
    try:
        x1, y1, x2, y2 = bbox
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image_array.shape[1], x2), min(image_array.shape[0], y2)
        if x2 <= x1 or y2 <= y1:
            return None
        face_img = image_array[y1:y2, x1:x2]
        if face_img.size == 0:
            return None
        embedding = face_model.get_feat(face_img)
        if embedding is not None:
            return embedding / np.linalg.norm(embedding)
    except Exception as e:
        print(f"extract_embedding error: {e}")
    return None


def cosine_similarity(a, b):
    if b.size == 0:
        return np.array([])
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return np.dot(b_norm, a_norm).flatten()


def save_student_embeddings(student_id, student_name, embeddings):
    try:
        emb_filename = f"{student_id}.npy"
        np.save(str(ENCODINGS_DIR / emb_filename), embeddings.astype(np.float32))
        index = {}
        if INDEX_FILE.exists():
            with open(INDEX_FILE) as f:
                index = json.load(f)
        index[str(student_id)] = {"name": student_name, "file": emb_filename}
        with open(INDEX_FILE, "w") as f:
            json.dump(index, f, indent=2)
        return True
    except Exception as e:
        print(f"save_student_embeddings error: {e}")
        return False


def recognize_face_in_image(image_path, threshold=RECOGNITION_THRESHOLD):
    if not insightface_app:
        return {"success": False, "error": "InsightFace not initialised"}

    names_db, vecs_db = load_all_embeddings()
    if vecs_db.size == 0:
        return {"success": False, "error": "No embeddings found. Encode faces first."}

    try:
        pil_image = ImageOps.exif_transpose(Image.open(str(image_path)))
        img_bgr   = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    except Exception:
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            return {"success": False, "error": "Failed to read image"}

    img_rgb  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    faces    = detect_faces(img_rgb)
    if not faces:
        return {"success": False, "error": "No faces detected"}

    annotated    = img_bgr.copy()
    recognitions = []
    marked_count = 0

    for face in faces:
        bbox = face["bbox"]
        x1, y1, x2, y2 = bbox
        emb  = np.array(face["embedding"]) if face.get("embedding") else extract_embedding(img_rgb, bbox)
        name = "Unknown"
        confidence = 0.0

        if emb is not None and vecs_db.size > 0:
            sims = cosine_similarity(emb, vecs_db)
            if sims.size:
                best_idx = np.argmax(sims)
                best_sim = sims[best_idx]
                if best_sim >= threshold:
                    name       = names_db[best_idx]
                    confidence = float(best_sim)
                    marked_count += 1

        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(annotated, f"{name} ({confidence:.2f})", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        recognitions.append({"name": name, "confidence": confidence, "bbox": bbox})

    ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name   = image_path.stem.lstrip("annotated_")
    ann_filename = f"annotated_{clean_name}_{ts}.jpg"
    ann_path     = UPLOADS_DIR / ann_filename
    cv2.imwrite(str(ann_path), annotated)
    save_thumbnail(ann_path)

    _, buf = cv2.imencode(".jpg", annotated)
    return {
        "success":            True,
        "faces_found":        len(faces),
        "recognized":         marked_count,
        "recognitions":       recognitions,
        "annotated_image":    f"data:image/jpeg;base64,{base64.b64encode(buf).decode()}",
        "annotated_path":     str(ann_path),
        "annotated_filename": ann_filename,
    }


def cleanup_old_annotated_files(max_files=20):
    try:
        files = sorted(UPLOADS_DIR.glob("annotated_*.jpg"), key=lambda x: x.stat().st_mtime)
        for f in files[:-max_files]:
            f.unlink()
            thumb = THUMB_DIR / f"thumb_{f.name}"
            if thumb.exists():
                thumb.unlink()
    except Exception as e:
        print(f"cleanup error: {e}")


def update_student_statistics():
    db = get_db()
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            index = json.load(f)
        for sid_str, info in index.items():
            emb_file = ENCODINGS_DIR / (info["file"] if isinstance(info, dict) else info)
            if emb_file.exists():
                data       = np.load(str(emb_file))
                face_count = data.shape[0] if data.ndim > 1 else 1
                db.students.update_one(
                    {"_id": oid(sid_str)},
                    {"$set": {"face_count": face_count}}
                )
    for student in db.students.find():
        present = db.attendance.count_documents({"student_id": student["_id"], "status": "present"})
        db.students.update_one({"_id": student["_id"]}, {"$set": {"attendance_count": present}})

# ==================== BACKGROUND ENCODING ====================
_encoding_progress = {"running": False, "progress": 0, "total": 0, "done": 0, "status": "idle", "error": None}
_encoding_lock     = threading.Lock()


def _run_encoding_thread():
    global _encoding_progress
    try:
        folders = [d for d in DATASET_DIR.iterdir() if d.is_dir()]
        total   = len(folders)
        with _encoding_lock:
            _encoding_progress.update({"running": True, "progress": 0, "total": total,
                                       "done": 0, "status": "running", "error": None,
                                       "message": "Starting…"})
        total_emb = 0
        processed = 0
        for i, folder in enumerate(folders):
            student_id_str = folder.name
            name_file      = folder / "name.txt"
            student_name   = name_file.read_text(encoding="utf-8").strip() if name_file.exists() else student_id_str

            embeddings = []
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
                for img_path in folder.glob(ext):
                    try:
                        arr   = np.array(Image.open(str(img_path)).convert("RGB"))
                        faces = detect_faces(arr)
                        if faces:
                            face = faces[0]
                            emb  = np.array(face["embedding"]) if face.get("embedding") else extract_embedding(arr, face["bbox"])
                            if emb is not None:
                                embeddings.append(emb)
                                total_emb += 1
                    except Exception as e:
                        print(f"Encoding error ({img_path}): {e}")

            if embeddings:
                save_student_embeddings(student_id_str, student_name, np.vstack(embeddings))
                processed += 1

            with _encoding_lock:
                done = i + 1
                _encoding_progress.update({
                    "done":     done,
                    "progress": int(done / total * 100) if total else 100,
                    "message":  f"Processing {student_name}… ({done}/{total})",
                })

        invalidate_embeddings_cache()
        update_student_statistics()
        with _encoding_lock:
            _encoding_progress.update({"running": False, "progress": 100, "status": "complete",
                                       "message": f"Encoded {total_emb} faces for {processed} students."})
    except Exception as e:
        with _encoding_lock:
            _encoding_progress.update({"running": False, "status": "error",
                                       "error": str(e), "message": f"Encoding failed: {e}"})

# ==================== AUTH DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("user_role") not in roles:
                flash("Permission denied.", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ==================== STATIC FILE ROUTES ====================

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)

@app.route("/uploads/thumbs/<filename>")
def uploaded_thumb(filename):
    return send_from_directory(THUMB_DIR, filename)

# ==================== AUTH ROUTES ====================

@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Username and password required.", "error")
            return render_template("login.html")
        db   = get_db()
        user = db.users.find_one({"username": username})
        if user and check_password_hash(user["password_hash"], password):
            session.update({
                "user_id":    str(user["_id"]),
                "username":   user["username"],
                "user_role":  user["role"],
                "full_name":  user.get("full_name") or user["username"],
                "department": user.get("department") or "",
                "student_id": str(user["student_id"]) if user.get("student_id") else None,
            })
            flash(f'Welcome back, {session["full_name"]}!', "success")
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))

# ==================== DASHBOARD ====================

@app.route("/index")
@login_required
def index():
    db    = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    today_session_ids = [s["_id"] for s in db.sessions.find({"date": today})]
    stats = {
        "total_students":   db.students.count_documents({}),
        "today_sessions":   len(today_session_ids),
        "today_attendance": db.attendance.count_documents(
            {"session_id": {"$in": today_session_ids}, "status": "present"}
        ) if today_session_ids else 0,
        "total_attendance": db.attendance.count_documents({"status": "present"}),
    }

    top_students = []
    for student in db.students.find():
        total = db.attendance.count_documents({"student_id": student["_id"]})
        if total == 0:
            continue
        present = db.attendance.count_documents({"student_id": student["_id"], "status": "present"})
        top_students.append({
            "name":          student["name"],
            "department":    student.get("department"),
            "present_count": present,
            "total_count":   total,
            "percentage":    round(present / total * 100, 1),
        })
    top_students = sorted(top_students, key=lambda x: x["percentage"], reverse=True)[:5]

    recent_sessions = []
    for s in db.sessions.find().sort("date", -1).limit(5):
        subject = db.subjects.find_one({"_id": s["subject_id"]}) or {}
        teacher = db.users.find_one({"_id": s["teacher_id"]}) or {}
        present = db.attendance.count_documents({"session_id": s["_id"], "status": "present"})
        recent_sessions.append({
            "id":            str(s["_id"]),
            "date":          s["date"],
            "start_time":    s["start_time"],
            "end_time":      s["end_time"],
            "subject_name":  subject.get("subject_name", ""),
            "teacher_name":  teacher.get("full_name", ""),
            "present_count": present,
        })

    subjects = list(db.subjects.find().sort("subject_name", 1))
    teachers = list(db.users.find({"role": "teacher"}).sort("full_name", 1))
    for doc in subjects + teachers:
        doc["id"] = str(doc["_id"])

    return render_template("index.html",
                           stats=stats,
                           top_students=top_students,
                           recent_sessions=recent_sessions,
                           subjects=subjects,
                           teachers=teachers,
                           encodings_exist=INDEX_FILE.exists() and INDEX_FILE.stat().st_size > 0,
                           insightface_available=INSIGHTFACE_AVAILABLE and insightface_app is not None)


@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("index"))

# ==================== CAPTURE ====================

@app.route("/capture")
@login_required
@role_required("admin", "teacher")
def capture_page():
    db       = get_db()
    subjects = list(db.subjects.find().sort("subject_name", 1))
    teachers = list(db.users.find({"role": "teacher"}).sort("full_name", 1))
    students = list(db.students.find().sort("name", 1))
    for doc in subjects + teachers + students:
        doc["id"] = str(doc["_id"])
    return render_template("capture.html",
                           subjects=subjects,
                           teachers=teachers,
                           student_count=db.students.count_documents({}),
                           students=students)


@app.route("/upload_photo", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def upload_photo():
    try:
        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = UPLOADS_DIR / filename
                file.save(str(filepath))
                save_thumbnail(filepath)
                return jsonify({"success": True, "filename": filename})
        elif "imageData" in request.form:
            image_data = request.form["imageData"]
            if "," in image_data:
                image_data = image_data.split(",")[1]
            image = Image.open(BytesIO(base64.b64decode(image_data))).convert("RGB")
            filename = f"class_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = UPLOADS_DIR / filename
            image.save(str(filepath), "JPEG", quality=90)
            save_thumbnail(filepath)
            return jsonify({"success": True, "filename": filename})
        return jsonify({"success": False, "error": "Invalid format"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/recognize", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def recognize():
    try:
        if "image" in request.files:
            file = request.files["image"]
            if not (file and allowed_file(file.filename)):
                return jsonify({"success": False, "error": "Invalid image"}), 400
            filename = f"recognize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = UPLOADS_DIR / filename
            file.save(str(filepath))
            latest_photo = filepath
        else:
            photos = [f for f in list(UPLOADS_DIR.glob("*.jpg")) + list(UPLOADS_DIR.glob("*.png"))
                      if not f.name.startswith("annotated_")]
            if not photos:
                return jsonify({"success": False, "error": "No photos found. Capture first."}), 400
            latest_photo = max(photos, key=lambda f: f.stat().st_ctime)

        subject_id = request.form.get("subject_id")
        teacher_id = request.form.get("teacher_id", session.get("user_id"))
        threshold  = float(request.form.get("threshold", RECOGNITION_THRESHOLD))

        if not subject_id:
            return jsonify({"success": False, "error": "Please select a subject"}), 400
        if not INSIGHTFACE_AVAILABLE or not insightface_app:
            return jsonify({"success": False, "error": "Face recognition not available"}), 500

        result = recognize_face_in_image(latest_photo, threshold=threshold)
        if not result.get("success"):
            return jsonify(result), 400

        db          = get_db()
        today       = datetime.now().strftime("%Y-%m-%d")
        start       = datetime.now().strftime("%H:%M")
        end         = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
        subj_oid    = oid(subject_id)
        teacher_oid = oid(teacher_id)

        existing = db.sessions.find_one({
            "subject_id": subj_oid, "teacher_id": teacher_oid,
            "date": today, "start_time": start, "end_time": end,
        })
        if existing:
            session_id = existing["_id"]
        else:
            session_id = db.sessions.insert_one({
                "subject_id": subj_oid, "teacher_id": teacher_oid,
                "date": today, "start_time": start, "end_time": end,
                "created_at": datetime.now(),
            }).inserted_id

        marked_students = []
        for rec in result["recognitions"]:
            if rec["name"] == "Unknown" or rec["confidence"] < threshold:
                continue
            student = db.students.find_one({"name": rec["name"]})
            if not student:
                new_id      = db.students.insert_one({
                    "name": rec["name"], "roll_no": None, "department": None,
                    "year": None, "face_count": 0, "attendance_count": 0,
                    "created_at": datetime.now(),
                }).inserted_id
                student_oid = new_id
                student_dir = DATASET_DIR / str(new_id)
                student_dir.mkdir(parents=True, exist_ok=True)
                (student_dir / "name.txt").write_text(rec["name"], encoding="utf-8")
            else:
                student_oid = student["_id"]

            db.attendance.update_one(
                {"session_id": session_id, "student_id": student_oid},
                {"$set": {"status": "present", "confidence": rec["confidence"],
                          "marked_at": datetime.now()}},
                upsert=True,
            )
            marked_students.append(rec["name"])

        for student in db.students.find():
            db.attendance.update_one(
                {"session_id": session_id, "student_id": student["_id"]},
                {"$setOnInsert": {"status": "absent", "confidence": None,
                                  "marked_at": datetime.now()}},
                upsert=True,
            )

        subject = db.subjects.find_one({"_id": subj_oid}) or {}
        teacher = db.users.find_one({"_id": teacher_oid}) or {}
        append_to_timeline(latest_photo.name, len(marked_students), result["faces_found"],
                           subject.get("subject_name", ""), teacher.get("full_name", ""))
        update_student_statistics()
        cleanup_old_annotated_files()

        return jsonify({
            "success":         True,
            "message":         f"Attendance marked for {len(marked_students)} students",
            "faces_found":     result["faces_found"],
            "recognized":      len(marked_students),
            "annotated_image": result.get("annotated_image"),
            "marked_students": marked_students,
        })
    except Exception as e:
        print(f"Recognition error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== STUDENTS ====================

@app.route("/students", methods=["GET", "POST"])
@login_required
@role_required("admin")
def students():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "add":
            name       = request.form.get("name", "").strip()
            roll_no    = request.form.get("roll_no", "").strip() or None
            department = request.form.get("department", "").strip() or None
            username   = request.form.get("username", "").strip()
            password   = request.form.get("password", "").strip()
            year_raw   = request.form.get("year", "").strip()
            year       = int(year_raw) if year_raw and year_raw.isdigit() else None

            if not name:
                return jsonify({"success": False, "error": "Name required."}), 400
            if not username or not password:
                return jsonify({"success": False, "error": "Username and password required."}), 400
            if len(password) < 6:
                return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400
            if db.users.find_one({"username": username}):
                return jsonify({"success": False, "error": "Username already exists."}), 400
            if not roll_no and db.students.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}):
                return jsonify({"success": False, "error": "A student with this name already exists. Provide a roll number."}), 400
            if roll_no and db.students.find_one({"roll_no": roll_no}):
                return jsonify({"success": False, "error": "Roll number already exists."}), 400

            student_id = db.students.insert_one({
                "name": name, "roll_no": roll_no, "department": department,
                "year": year, "face_count": 0, "attendance_count": 0,
                "created_at": datetime.now(),
            }).inserted_id

            # NOTE: student_id is a real ObjectId here — safe to include
            db.users.insert_one({
                "username":      username,
                "password_hash": generate_password_hash(password),
                "role":          "student",
                "full_name":     name,
                "department":    department,
                "student_id":    student_id,
                "created_at":    datetime.now(),
            })

            student_dir = DATASET_DIR / str(student_id)
            student_dir.mkdir(parents=True, exist_ok=True)
            (student_dir / "name.txt").write_text(name, encoding="utf-8")

            if "images" in request.files:
                for file in request.files.getlist("images"):
                    if file and file.filename and allowed_file(file.filename):
                        fname    = secure_filename(file.filename)
                        filepath = student_dir / fname
                        save_file_copy(file, filepath)
                        save_thumbnail(filepath)

            return jsonify({"success": True, "message": f"Student added. Username: {username}"})

        elif action == "edit":
            student_id = request.form.get("student_id", "").strip()
            name       = request.form.get("name", "").strip()
            roll_no    = request.form.get("roll_no", "").strip() or None
            department = request.form.get("department", "").strip() or None
            username   = request.form.get("username", "").strip()
            password   = request.form.get("password", "").strip()
            year_raw   = request.form.get("year", "").strip()
            year       = int(year_raw) if year_raw and year_raw.isdigit() else None

            if not name or not student_id:
                return jsonify({"success": False, "error": "Name and ID required."}), 400

            sid = oid(student_id)
            if not db.students.find_one({"_id": sid}):
                return jsonify({"success": False, "error": "Student not found."}), 404
            if roll_no and db.students.find_one({"roll_no": roll_no, "_id": {"$ne": sid}}):
                return jsonify({"success": False, "error": "Roll number already exists."}), 400

            db.students.update_one(
                {"_id": sid},
                {"$set": {"name": name, "roll_no": roll_no, "department": department, "year": year}}
            )

            user = db.users.find_one({"student_id": sid})
            if user:
                update_fields = {"full_name": name, "department": department}
                if username:
                    update_fields["username"] = username
                if password:
                    if len(password) < 6:
                        return jsonify({"success": False, "error": "Password min 6 chars."}), 400
                    update_fields["password_hash"] = generate_password_hash(password)
                db.users.update_one({"_id": user["_id"]}, {"$set": update_fields})
            else:
                if not username or not password:
                    return jsonify({"success": False, "error": "Username and password required."}), 400
                db.users.insert_one({
                    "username":      username,
                    "password_hash": generate_password_hash(password),
                    "role":          "student",
                    "full_name":     name,
                    "department":    department,
                    "student_id":    sid,
                    "created_at":    datetime.now(),
                })

            student_dir = DATASET_DIR / str(student_id)
            student_dir.mkdir(parents=True, exist_ok=True)
            (student_dir / "name.txt").write_text(name, encoding="utf-8")

            if INDEX_FILE.exists():
                with open(INDEX_FILE) as f:
                    index = json.load(f)
                if student_id in index:
                    index[student_id]["name"] = name
                    with open(INDEX_FILE, "w") as f:
                        json.dump(index, f, indent=2)
                    invalidate_embeddings_cache()

            return jsonify({"success": True, "message": "Student updated."})

        elif action == "delete":
            student_id = request.form.get("student_id", "").strip()
            if not student_id:
                flash("Student ID required.", "error")
                return redirect(url_for("students"))
            sid     = oid(student_id)
            student = db.students.find_one({"_id": sid})
            if student:
                db.users.delete_one({"student_id": sid})
                db.attendance.delete_many({"student_id": sid})
                db.students.delete_one({"_id": sid})
                import shutil
                student_dir = DATASET_DIR / str(student_id)
                if student_dir.exists():
                    shutil.rmtree(student_dir)
                emb_file = ENCODINGS_DIR / f"{student_id}.npy"
                if emb_file.exists():
                    emb_file.unlink()
                if INDEX_FILE.exists():
                    with open(INDEX_FILE) as f:
                        index = json.load(f)
                    if student_id in index:
                        del index[student_id]
                        with open(INDEX_FILE, "w") as f:
                            json.dump(index, f, indent=2)
                invalidate_embeddings_cache()
                flash(f'Student "{student["name"]}" deleted.', "success")
            else:
                flash("Student not found.", "error")
            return redirect(url_for("students"))

    # GET
    search     = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    query      = {}
    if search:
        query["$or"] = [
            {"name":    {"$regex": search, "$options": "i"}},
            {"roll_no": {"$regex": search, "$options": "i"}},
        ]
    if department:
        query["department"] = department

    students_list = []
    for student in db.students.find(query).sort("name", 1):
        user = db.users.find_one({"student_id": student["_id"]})
        student["id"]       = str(student["_id"])
        student["username"] = user["username"] if user else ""
        students_list.append(student)

    departments = [d for d in db.students.distinct("department") if d]

    return render_template("students.html",
                           students=students_list,
                           departments=departments,
                           search=search,
                           selected_department=department)

# ==================== SUBJECTS ====================

@app.route("/subjects", methods=["GET", "POST"])
@login_required
@role_required("admin")
def subjects_page():
    db = get_db()
    if request.method == "POST":
        subject_name = request.form.get("subject_name", "").strip()
        department   = request.form.get("department", "General").strip()
        if not subject_name:
            flash("Subject name required.", "error")
            return redirect(url_for("subjects_page"))
        # Do NOT include teacher_id at insert time to avoid sparse index issues
        db.subjects.insert_one({
            "subject_name": subject_name,
            "department":   department,
            "created_at":   datetime.now(),
        })
        flash(f'Subject "{subject_name}" added.', "success")
        return redirect(url_for("subjects_page"))

    subjects = []
    for s in db.subjects.find().sort("subject_name", 1):
        teacher = db.users.find_one({"_id": s["teacher_id"]}) if s.get("teacher_id") else None
        s["id"]           = str(s["_id"])
        s["teacher_name"] = teacher["full_name"] if teacher else ""
        s["created_at"]   = fmt_created_at(s)   # ← safe fallback
        subjects.append(s)

    teachers = list(db.users.find({"role": "teacher"}).sort("full_name", 1))
    for t in teachers:
        t["id"] = str(t["_id"])

    return render_template("subjects.html", subjects=subjects, teachers=teachers)


@app.route("/subjects/delete/<subject_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_subject(subject_id):
    db  = get_db()
    sid = oid(subject_id)
    if db.sessions.find_one({"subject_id": sid}):
        flash("Cannot delete a subject that has sessions.", "error")
    else:
        db.subjects.delete_one({"_id": sid})
        flash("Subject deleted.", "success")
    return redirect(url_for("subjects_page"))


@app.route("/subjects/assign_teacher", methods=["POST"])
@login_required
@role_required("admin")
def assign_subject_teacher():
    db         = get_db()
    subject_id = request.form.get("subject_id")
    teacher_id = request.form.get("teacher_id")
    if not subject_id or not teacher_id:
        flash("Subject and teacher required.", "error")
        return redirect(url_for("subjects_page"))
    db.subjects.update_one({"_id": oid(subject_id)}, {"$set": {"teacher_id": oid(teacher_id)}})
    flash("Teacher assigned.", "success")
    return redirect(url_for("subjects_page"))

# ==================== USERS ====================

@app.route("/users")
@login_required
@role_required("admin")
def users_page():
    db    = get_db()
    users = list(db.users.find().sort("username", 1))
    for u in users:
        u["id"] = str(u["_id"])
    return render_template("users.html", users=users)


@app.route("/users/add", methods=["POST"])
@login_required
@role_required("admin")
def add_user():
    db         = get_db()
    username   = request.form.get("username", "").strip()
    password   = request.form.get("password", "").strip()
    role       = request.form.get("role", "student")
    full_name  = request.form.get("full_name", "").strip()
    department = request.form.get("department", "").strip()
    email      = request.form.get("email", "").strip()

    if not username or not password:
        flash("Username and password required.", "error")
        return redirect(url_for("users_page"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("users_page"))
    if db.users.find_one({"username": username}):
        flash(f'Username "{username}" already exists.', "error")
        return redirect(url_for("users_page"))

    # NOTE: Do NOT include student_id field for admin/teacher users —
    # sparse unique index allows missing field but not multiple nulls.
    db.users.insert_one({
        "username":      username,
        "password_hash": generate_password_hash(password),
        "role":          role,
        "full_name":     full_name,
        "department":    department,
        "email":         email,
        "created_at":    datetime.now(),
    })
    flash(f'User "{username}" added.', "success")
    return redirect(url_for("users_page"))


@app.route("/users/delete/<user_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_user(user_id):
    db    = get_db()
    uid   = oid(user_id)
    force = request.form.get("force") == "1"

    if str(uid) == session.get("user_id"):
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("users_page"))

    user = db.users.find_one({"_id": uid})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("users_page"))

    if user["role"] == "teacher":
        session_count = db.sessions.count_documents({"teacher_id": uid})
        if session_count > 0:
            if force:
                db.sessions.delete_many({"teacher_id": uid})
            else:
                flash(f'Teacher has {session_count} session(s). Use force delete to remove them.', "error")
                return redirect(url_for("users_page"))

    db.subjects.update_many({"teacher_id": uid}, {"$unset": {"teacher_id": ""}})
    db.users.delete_one({"_id": uid})
    flash(f'User "{user["username"]}" deleted.', "success")
    return redirect(url_for("users_page"))

# ==================== SESSIONS ====================

@app.route("/create_session", methods=["GET", "POST"])
@login_required
@role_required("admin", "teacher")
def create_session_page():
    db = get_db()
    if request.method == "POST":
        subject_id = request.form.get("subject_id")
        teacher_id = request.form.get("teacher_id", session.get("user_id"))
        date       = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time   = request.form.get("end_time")

        if not all([subject_id, date, start_time, end_time]):
            flash("All fields are required.", "error")
            return redirect(url_for("create_session_page"))
        if start_time >= end_time:
            flash("End time must be after start time.", "error")
            return redirect(url_for("create_session_page"))

        subj_oid    = oid(subject_id)
        teacher_oid = oid(teacher_id)

        if not db.subjects.find_one({"_id": subj_oid}):
            flash("Subject does not exist.", "error")
            return redirect(url_for("create_session_page"))
        if not db.users.find_one({"_id": teacher_oid, "role": "teacher"}):
            flash("Teacher does not exist.", "error")
            return redirect(url_for("create_session_page"))
        if db.sessions.find_one({"subject_id": subj_oid, "teacher_id": teacher_oid,
                                  "date": date, "start_time": start_time, "end_time": end_time}):
            flash("A session with these details already exists.", "warning")
            return redirect(url_for("create_session_page"))

        session_oid = db.sessions.insert_one({
            "subject_id": subj_oid, "teacher_id": teacher_oid,
            "date": date, "start_time": start_time, "end_time": end_time,
            "created_at": datetime.now(),
        }).inserted_id

        for student in db.students.find():
            db.attendance.update_one(
                {"session_id": session_oid, "student_id": student["_id"]},
                {"$setOnInsert": {"status": "absent", "confidence": None,
                                  "marked_at": datetime.now()}},
                upsert=True,
            )

        flash(f"Session created! (ID: {session_oid})", "success")
        return redirect(url_for("attendance", subject_id=subject_id,
                                teacher_id=teacher_id, start_date=date, end_date=date))

    subjects = list(db.subjects.find().sort("subject_name", 1))
    teachers = list(db.users.find({"role": "teacher"}).sort("full_name", 1))
    for doc in subjects + teachers:
        doc["id"] = str(doc["_id"])

    recent_sessions = []
    for s in db.sessions.find().sort("date", -1).limit(5):
        subject = db.subjects.find_one({"_id": s["subject_id"]}) or {}
        teacher = db.users.find_one({"_id": s["teacher_id"]}) or {}
        present = db.attendance.count_documents({"session_id": s["_id"], "status": "present"})
        recent_sessions.append({
            "id":            str(s["_id"]),
            "date":          s["date"],
            "start_time":    s["start_time"],
            "subject_name":  subject.get("subject_name", ""),
            "teacher_name":  teacher.get("full_name", ""),
            "present_count": present,
        })

    return render_template("create_session.html",
                           subjects=subjects, teachers=teachers,
                           recent_sessions=recent_sessions)


@app.route("/session/reset/<session_id>", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def reset_session(session_id):
    db  = get_db()
    sid = oid(session_id)
    if not db.sessions.find_one({"_id": sid}):
        flash("Session not found.", "error")
        return redirect(url_for("attendance"))
    db.attendance.update_many({"session_id": sid},
                              {"$set": {"status": "absent", "confidence": None}})
    flash(f"Session attendance reset.", "success")
    return redirect(url_for("attendance", session_id=session_id))


@app.route("/sessions/delete/<session_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_session(session_id):
    db  = get_db()
    sid = oid(session_id)
    if not db.sessions.find_one({"_id": sid}):
        flash("Session not found.", "error")
    else:
        db.sessions.delete_one({"_id": sid})
        db.attendance.delete_many({"session_id": sid})
        flash("Session deleted.", "success")
    return redirect(url_for("attendance"))

# ==================== ATTENDANCE ====================

@app.route("/attendance")
@login_required
def attendance():
    db         = get_db()
    subject_id = request.args.get("subject_id", "")
    teacher_id = request.args.get("teacher_id", "")
    start_date = request.args.get("start_date", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
    end_date   = request.args.get("end_date",   datetime.now().strftime("%Y-%m-%d"))

    subjects = list(db.subjects.find().sort("subject_name", 1))
    teachers = list(db.users.find({"role": "teacher"}).sort("full_name", 1))
    for doc in subjects + teachers:
        doc["id"] = str(doc["_id"])

    session_query = {"date": {"$gte": start_date, "$lte": end_date}}
    if subject_id:
        session_query["subject_id"] = oid(subject_id)
    if teacher_id:
        session_query["teacher_id"] = oid(teacher_id)

    sessions_raw = list(db.sessions.find(session_query).sort([("date", -1), ("start_time", -1)]))
    session_oids = [s["_id"] for s in sessions_raw]

    sessions_list = []
    for s in sessions_raw:
        subject = db.subjects.find_one({"_id": s["subject_id"]}) or {}
        teacher = db.users.find_one({"_id": s["teacher_id"]}) or {}
        sessions_list.append({
            "id":           str(s["_id"]),
            "date":         s["date"],
            "start_time":   s["start_time"],
            "end_time":     s["end_time"],
            "subject_name": subject.get("subject_name", ""),
            "teacher_name": teacher.get("full_name", ""),
        })

    student_filter = {}
    if session.get("user_role") == "student" and session.get("student_id"):
        student_filter = {"_id": oid(session["student_id"])}

    attendance_summary = []
    defaulters         = []

    for student in db.students.find(student_filter).sort("name", 1):
        sid     = student["_id"]
        att     = list(db.attendance.find({"student_id": sid, "session_id": {"$in": session_oids}}))
        total   = len(att)
        present = sum(1 for a in att if a["status"] == "present")
        pct     = round(present / total * 100, 1) if total > 0 else 0

        row = {
            "id":                 str(sid),
            "name":               student["name"],
            "roll_no":            student.get("roll_no"),
            "department":         student.get("department"),
            "present_count":      present,
            "total_sessions":     total,
            "attendance_percent": pct,
            "session_attendance": {str(a["session_id"]): a["status"] for a in att},
        }
        attendance_summary.append(row)
        if pct < 75 and total >= 3:
            defaulters.append(row)

    recent_sessions = []
    for s in db.sessions.find().sort("date", -1).limit(5):
        subject = db.subjects.find_one({"_id": s["subject_id"]}) or {}
        teacher = db.users.find_one({"_id": s["teacher_id"]}) or {}
        present = db.attendance.count_documents({"session_id": s["_id"], "status": "present"})
        recent_sessions.append({
            "id":            str(s["_id"]),
            "date":          s["date"],
            "start_time":    s["start_time"],
            "subject_name":  subject.get("subject_name", ""),
            "teacher_name":  teacher.get("full_name", ""),
            "present_count": present,
        })

    return render_template("attendance.html",
                           subjects=subjects, teachers=teachers,
                           sessions=sessions_list,
                           attendance_summary=attendance_summary,
                           defaulters=defaulters,
                           recent_sessions=recent_sessions,
                           total_sessions=len(sessions_list),
                           selected_subject_id=subject_id,
                           selected_teacher_id=teacher_id,
                           selected_subject_name=next((s["subject_name"] for s in subjects if s["id"] == subject_id), "All Subjects"),
                           selected_teacher_name=next((t["full_name"] for t in teachers if t["id"] == teacher_id), "All Teachers"),
                           start_date=start_date, end_date=end_date)


@app.route("/admin/reset_attendance", methods=["POST"])
@login_required
@role_required("admin")
def reset_attendance():
    db            = get_db()
    session_count = db.sessions.count_documents({})
    att_count     = db.attendance.count_documents({})
    db.sessions.delete_many({})
    db.attendance.delete_many({})
    flash(f"✅ Reset complete. Deleted {session_count} sessions and {att_count} records.", "success")
    return redirect(url_for("users_page"))

# ==================== MANUAL ATTENDANCE ====================

@app.route("/session/<session_id>/mark_manual", methods=["POST"])
@login_required
@role_required("admin", "teacher")
def mark_attendance_manual(session_id):
    db         = get_db()
    student_id = request.form.get("student_id")
    if not student_id:
        return jsonify({"success": False, "error": "Student ID required"}), 400

    sid  = oid(session_id)
    stid = oid(student_id)

    if not db.sessions.find_one({"_id": sid}):
        return jsonify({"success": False, "error": "Session not found"}), 404
    student = db.students.find_one({"_id": stid})
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404

    db.attendance.update_one(
        {"session_id": sid, "student_id": stid},
        {"$set": {"status": "present", "confidence": None, "marked_at": datetime.now()}},
        upsert=True,
    )
    return jsonify({"success": True, "message": f'Marked {student["name"]} present'})

# ==================== REPORTS ====================

@app.route("/download_attendance_report")
@login_required
def download_attendance_report():
    db         = get_db()
    subject_id = request.args.get("subject_id", "")
    teacher_id = request.args.get("teacher_id", "")
    start_date = request.args.get("start_date", "")
    end_date   = request.args.get("end_date", "")

    session_query = {}
    if subject_id:
        session_query["subject_id"] = oid(subject_id)
    if teacher_id:
        session_query["teacher_id"] = oid(teacher_id)
    if start_date or end_date:
        session_query["date"] = {}
        if start_date:
            session_query["date"]["$gte"] = start_date
        if end_date:
            session_query["date"]["$lte"] = end_date

    sessions_raw = list(db.sessions.find(session_query))
    session_oids = [s["_id"] for s in sessions_raw]
    session_map  = {s["_id"]: s for s in sessions_raw}

    rows = []
    for att in db.attendance.find({"session_id": {"$in": session_oids}}).sort("marked_at", -1):
        s       = session_map.get(att["session_id"], {})
        student = db.students.find_one({"_id": att["student_id"]}) or {}
        subject = db.subjects.find_one({"_id": s.get("subject_id")}) or {}
        teacher = db.users.find_one({"_id": s.get("teacher_id")}) or {}
        rows.append({
            "roll_no":    student.get("roll_no", ""),
            "name":       student.get("name", ""),
            "department": student.get("department", ""),
            "subject":    subject.get("subject_name", ""),
            "teacher":    teacher.get("full_name", ""),
            "date":       s.get("date", ""),
            "start_time": s.get("start_time", ""),
            "end_time":   s.get("end_time", ""),
            "status":     att.get("status", ""),
            "confidence": att.get("confidence"),
            "marked_at":  str(att.get("marked_at", "")),
        })

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# Attendance Report"])
    writer.writerow([f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])
    writer.writerow(["Roll No", "Student Name", "Department", "Subject", "Teacher",
                     "Date", "Start Time", "End Time", "Status", "Confidence", "Marked At"])
    present_count = 0
    for row in rows:
        if row["status"] == "present":
            present_count += 1
        writer.writerow([row["roll_no"], row["name"], row["department"], row["subject"],
                         row["teacher"], row["date"], row["start_time"], row["end_time"],
                         row["status"],
                         f"{row['confidence']:.2f}" if row["confidence"] else "",
                         row["marked_at"]])
    writer.writerow([])
    writer.writerow(["# Summary"])
    writer.writerow(["Total", len(rows), "Present", present_count, "Absent", len(rows) - present_count])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=attendance_{ts}.csv"})


# attendance/excel redirects to CSV (template calls this endpoint)
@app.route("/attendance/excel")
@login_required
def download_attendance_excel():
    return redirect(url_for("download_attendance_report",
                            subject_id=request.args.get("subject_id", ""),
                            teacher_id=request.args.get("teacher_id", ""),
                            start_date=request.args.get("start_date", ""),
                            end_date=request.args.get("end_date", "")))


@app.route("/attendance/defaulters/export")
@login_required
def export_defaulters():
    db         = get_db()
    subject_id = request.args.get("subject_id", "")
    teacher_id = request.args.get("teacher_id", "")
    start_date = request.args.get("start_date", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
    end_date   = request.args.get("end_date",   datetime.now().strftime("%Y-%m-%d"))

    session_query = {"date": {"$gte": start_date, "$lte": end_date}}
    if subject_id:
        session_query["subject_id"] = oid(subject_id)
    if teacher_id:
        session_query["teacher_id"] = oid(teacher_id)

    session_oids = [s["_id"] for s in db.sessions.find(session_query)]

    defaulters = []
    for student in db.students.find():
        att   = list(db.attendance.find({"student_id": student["_id"], "session_id": {"$in": session_oids}}))
        total = len(att)
        if total < 3:
            continue
        present = sum(1 for a in att if a["status"] == "present")
        pct     = round(present / total * 100, 1)
        if pct < 75:
            defaulters.append({
                "name":       student["name"],
                "roll_no":    student.get("roll_no", ""),
                "department": student.get("department", ""),
                "present":    present,
                "total":      total,
                "percent":    pct,
            })

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# Defaulters Report (< 75% Attendance)"])
    writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])
    writer.writerow(["Name", "Roll No", "Department", "Present", "Total Sessions", "Attendance %"])
    for d in defaulters:
        writer.writerow([d["name"], d["roll_no"], d["department"],
                         d["present"], d["total"], f"{d['percent']}%"])
    writer.writerow([])
    writer.writerow(["Total Defaulters:", len(defaulters)])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=defaulters_{ts}.csv"})

# ==================== ENCODING ====================

@app.route("/encode", methods=["POST"])
@login_required
@role_required("admin")
def encode_faces():
    if not INSIGHTFACE_AVAILABLE or not insightface_app:
        flash("InsightFace not available.", "error")
        return redirect(url_for("index"))
    if not DATASET_DIR.exists() or not any(DATASET_DIR.iterdir()):
        flash("No student folders in dataset.", "error")
        return redirect(url_for("index"))
    with _encoding_lock:
        if _encoding_progress.get("running"):
            flash("Encoding already in progress.", "warning")
            return redirect(url_for("index"))
    threading.Thread(target=_run_encoding_thread, daemon=True).start()
    flash("Encoding started in background.", "success")
    return redirect(url_for("index"))


@app.route("/encode_status")
@login_required
def encode_status():
    with _encoding_lock:
        progress_copy = dict(_encoding_progress)
    total_students   = len([d for d in DATASET_DIR.iterdir() if d.is_dir()]) if DATASET_DIR.exists() else 0
    encoded_students = 0
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE) as f:
                encoded_students = len(json.load(f))
        except Exception:
            pass
    progress_copy["total_students"]   = total_students
    progress_copy["encoded_students"] = encoded_students
    return jsonify(progress_copy)

# ==================== API ENDPOINTS ====================

@app.route("/api/health")
def health_check():
    checks = {
        "database":    db_ping(),
        "insightface": INSIGHTFACE_AVAILABLE and insightface_app is not None,
        "directories": all(d.exists() for d in [DATASET_DIR, ENCODINGS_DIR, UPLOADS_DIR]),
    }
    return jsonify({"status": "healthy" if all(checks.values()) else "unhealthy", "checks": checks})


@app.route("/api/students")
@login_required
def api_students():
    db = get_db()
    return jsonify([
        {"id": str(s["_id"]), "name": s["name"], "roll_no": s.get("roll_no")}
        for s in db.students.find().sort("name", 1)
    ])


@app.route("/api/dashboard_stats")
@login_required
def dashboard_stats():
    db    = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    today_sids = [s["_id"] for s in db.sessions.find({"date": today})]
    return jsonify({"success": True, "stats": {
        "total_students":   db.students.count_documents({}),
        "today_sessions":   len(today_sids),
        "today_attendance": db.attendance.count_documents(
            {"session_id": {"$in": today_sids}, "status": "present"}
        ) if today_sids else 0,
        "total_attendance": db.attendance.count_documents({"status": "present"}),
    }})


@app.route("/api/capture_statistics")
@login_required
def capture_statistics():
    return jsonify({
        "success":          True,
        "total_faces":      0,
        "today_captures":   0,
        "storage_used":     "0 bytes",
        "encodings_ready":  INDEX_FILE.exists() and INDEX_FILE.stat().st_size > 0,
        "recognition_ready": INSIGHTFACE_AVAILABLE and insightface_app is not None,
    })


@app.route("/api/recent_captures")
@login_required
@role_required("admin", "teacher")
def recent_captures():
    try:
        image_files = []
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            image_files.extend(UPLOADS_DIR.glob(ext))
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        recent = []
        for file in image_files[:12]:
            stat       = file.stat()
            thumb_name = f"thumb_{file.name}"
            if not (THUMB_DIR / thumb_name).exists():
                save_thumbnail(file)
            recent.append({
                "id":        file.name,
                "filename":  file.name,
                "url":       f"/uploads/{file.name}",
                "thumbnail": f"/uploads/thumbs/{thumb_name}",
                "timestamp": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "time":      humanize.naturaltime(datetime.fromtimestamp(stat.st_mtime)) if HUMANIZE_AVAILABLE else datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "size":      humanize.naturalsize(stat.st_size) if HUMANIZE_AVAILABLE else f"{stat.st_size} bytes",
                "type":      "annotated" if file.name.startswith("annotated_") else "class",
            })
        return jsonify({"success": True, "captures": recent})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "captures": []})


@app.route("/api/delete_capture/<filename>", methods=["DELETE"])
@login_required
@role_required("admin", "teacher")
def delete_capture(filename):
    try:
        safe = secure_filename(filename)
        fp   = UPLOADS_DIR / safe
        if fp.exists():
            fp.unlink()
        tp = THUMB_DIR / f"thumb_{safe}"
        if tp.exists():
            tp.unlink()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload_student_faces", methods=["POST"])
@login_required
@role_required("admin")
def upload_student_faces():
    db         = get_db()
    student_id = request.form.get("student_id")
    if not student_id:
        return jsonify({"success": False, "error": "Student ID required"}), 400
    student = db.students.find_one({"_id": oid(student_id)})
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404

    student_dir = DATASET_DIR / str(student_id)
    student_dir.mkdir(parents=True, exist_ok=True)
    if not (student_dir / "name.txt").exists():
        (student_dir / "name.txt").write_text(student["name"], encoding="utf-8")

    uploaded = 0
    for file in request.files.getlist("images"):
        if file and file.filename and allowed_file(file.filename):
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname    = secure_filename(file.filename)
            filepath = student_dir / f"{ts}_{fname}"
            save_file_copy(file, filepath)
            save_thumbnail(filepath)
            uploaded += 1

    if uploaded:
        db.students.update_one({"_id": oid(student_id)}, {"$inc": {"face_count": uploaded}})
    return jsonify({"success": True, "message": f"Uploaded {uploaded} images", "uploaded": uploaded})


@app.route("/api/insightface_status")
def insightface_status():
    return jsonify({"available": INSIGHTFACE_AVAILABLE and insightface_app is not None})

# ==================== ERROR HANDLERS ====================

@app.errorhandler(413)
def too_large(e):
    return jsonify({"success": False, "error": "File too large (max 50MB)."}), 413

@app.errorhandler(404)
def not_found(e):
    return render_template("login.html"), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500

# ==================== MAIN ====================

if __name__ == "__main__":
    from init_db import init_database
    init_database()

    if INSIGHTFACE_AVAILABLE:
        init_insightface()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "app.log"),
            logging.StreamHandler(),
        ],
    )

    print("\n" + "=" * 50)
    print("🎯 AI Attendance System  [MongoDB edition]")
    print("=" * 50)
    print(f"🗄️  MongoDB: {os.environ.get('MONGO_URI', 'mongodb://localhost:27017')}")
    print(f"   Database: {os.environ.get('MONGO_DB', 'attendance_system')}")
    print(f"👤 Admin:   admin / admin123")
    print(f"👨‍🏫 Teacher: teacher1 / teacher123")
    print(f"👨‍🎓 Student: student1 / student123")
    print("=" * 50)
    print(f"🚀 http://0.0.0.0:{os.environ.get('PORT', 5001)}")
    print("=" * 50 + "\n")

    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))