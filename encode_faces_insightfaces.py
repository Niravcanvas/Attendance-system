#!/usr/bin/env python3
"""
encode_faces_insightfaces.py
Standalone script to encode faces using InsightFace.
Now uses student ID based folders and saves embeddings with ID.
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
from PIL import Image
import cv2

sys.path.insert(0, str(Path(__file__).parent))

try:
    import insightface
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("ERROR: InsightFace not installed. Install with: pip install insightface")
    sys.exit(1)

# ==================== CONFIGURATION ====================
BASE_DIR = Path(__file__).parent.absolute()
DATASET_DIR = BASE_DIR / "dataset"
ENCODINGS_DIR = BASE_DIR / "encodings"
INDEX_FILE = ENCODINGS_DIR / "index.json"
DB_PATH = BASE_DIR / "attendance.db"

DATASET_DIR.mkdir(exist_ok=True)
ENCODINGS_DIR.mkdir(exist_ok=True)

# ==================== INSIGHTFACE INIT ====================
def init_insightface():
    """Initialize InsightFace models"""
    try:
        print("Initializing InsightFace...")
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        model = get_model("buffalo_l", download=True)
        model.prepare(ctx_id=0)
        print("✅ InsightFace initialized successfully")
        return app, model
    except Exception as e:
        print(f"❌ Failed to initialize InsightFace: {e}")
        return None, None

# ==================== EMBEDDING EXTRACTION ====================
def extract_embedding(image_path, app, model):
    """Extract face embedding from an image"""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"  ❌ Failed to read image: {image_path}")
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = app.get(img_rgb)
        if not faces:
            print(f"  ⚠️  No faces detected in: {image_path.name}")
            return None

        face = faces[0]

        if hasattr(face, 'normed_embedding'):
            embedding = face.normed_embedding
        else:
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_rgb.shape[1], x2), min(img_rgb.shape[0], y2)
            if x2 <= x1 or y2 <= y1:
                print(f"  ⚠️  Invalid face bounding box in: {image_path.name}")
                return None
            face_img = img_rgb[y1:y2, x1:x2]
            if face_img.size == 0:
                print(f"  ⚠️  Empty face region in: {image_path.name}")
                return None
            embedding = model.get_feat(face_img)
            if embedding is not None:
                embedding = embedding / np.linalg.norm(embedding)
            else:
                print(f"  ⚠️  Failed to extract embedding from: {image_path.name}")
                return None

        return embedding

    except Exception as e:
        print(f"  ❌ Error processing {image_path.name}: {e}")
        return None

# ==================== SAVE EMBEDDINGS (matches app.py) ====================
def save_student_embeddings(student_id, student_name, embeddings):
    """Save embeddings for a student. student_id is used for filename."""
    try:
        emb_filename = f"{student_id}.npy"
        emb_path = ENCODINGS_DIR / emb_filename
        np.save(str(emb_path), embeddings.astype(np.float32))
        # Update index.json
        index = {}
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r') as f:
                index = json.load(f)
        index[str(student_id)] = {"name": student_name, "file": emb_filename}
        with open(INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving embeddings: {e}")
        return False

# ==================== INDEX HELPERS ====================
def load_existing_index():
    """Load existing embeddings index"""
    index = {}
    if INDEX_FILE.exists():
        try:
            with open(INDEX_FILE, 'r') as f:
                index = json.load(f)
            print(f"📁 Loaded existing index with {len(index)} students")
        except Exception as e:
            print(f"⚠️  Could not load existing index: {e}")
    return index

def save_index(index):
    """Save embeddings index"""
    try:
        with open(INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)
        print(f"💾 Saved index with {len(index)} students")
        return True
    except Exception as e:
        print(f"❌ Failed to save index: {e}")
        return False

# ==================== DATABASE STATISTICS ====================
def update_student_statistics():
    """Update face_count and attendance_count for all students"""
    if not DB_PATH.exists():
        print("⚠️  Database not found, skipping statistics update")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    try:
        # Sync face_count from actual .npy files
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r') as f:
                index = json.load(f)
            for student_id_str, info in index.items():
                if isinstance(info, dict):
                    emb_file = ENCODINGS_DIR / info["file"]
                else:
                    emb_file = ENCODINGS_DIR / info  # old format
                if emb_file.exists():
                    embeddings = np.load(str(emb_file))
                    face_count = embeddings.shape[0] if embeddings.ndim > 1 else 1
                    cursor.execute(
                        "UPDATE students SET face_count = ? WHERE id = ?",
                        (face_count, int(student_id_str) if student_id_str.isdigit() else -1)
                    )

        # Sync attendance_count from attendance table
        cursor.execute("""
            UPDATE students
            SET attendance_count = (
                SELECT COUNT(*)
                FROM attendance
                WHERE attendance.student_id = students.id AND attendance.status = 'present'
            )
        """)
        conn.commit()
        print("📊 Updated student statistics")
    except Exception as e:
        print(f"⚠️  Error updating statistics: {e}")
        conn.rollback()
    finally:
        conn.close()

# ==================== MAIN ENCODING LOGIC ====================
def main(args):
    """Main encoding function"""
    print("\n" + "="*60)
    print("🎭 FACE ENCODING UTILITY")
    print("="*60)

    if not DATASET_DIR.exists():
        print(f"❌ Dataset directory not found: {DATASET_DIR}")
        print("   Create a 'dataset' folder with student subfolders (named by student ID).")
        return False

    app, model = init_insightface()
    if app is None or model is None:
        return False

    index = load_existing_index()

    student_folders = sorted([d for d in DATASET_DIR.iterdir() if d.is_dir()])

    if not student_folders:
        print("❌ No student folders found in dataset.")
        print("   Create folders with student IDs containing face images and a name.txt file.")
        return False

    print(f"👥 Found {len(student_folders)} students in dataset")

    total_images = 0
    total_embeddings = 0
    processed_students = 0

    for folder in student_folders:
        student_id = folder.name
        # Try to read name from name.txt
        name_file = folder / "name.txt"
        if name_file.exists():
            student_name = name_file.read_text(encoding='utf-8').strip()
        else:
            print(f"⚠️  No name.txt in {folder}, using folder name as fallback")
            student_name = student_id

        print(f"\n📁 Processing: {student_name} (ID: {student_id})")

        # Skip if already encoded (unless --force)
        if not args.force and student_id in index:
            emb_path = ENCODINGS_DIR / f"{student_id}.npy"
            if emb_path.exists():
                embeddings = np.load(str(emb_path))
                count = embeddings.shape[0] if embeddings.ndim > 1 else 1
                print(f"  ⏭️  Skipping (already encoded, {count} embeddings)")
                continue

        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            image_files.extend(list(folder.glob(ext)))

        if not image_files:
            print(f"  ⚠️  No images found for {student_name}")
            continue

        print(f"  📸 Found {len(image_files)} images")

        embeddings = []
        for img_path in image_files:
            total_images += 1
            print(f"    Processing: {img_path.name}", end='', flush=True)
            embedding = extract_embedding(img_path, app, model)
            if embedding is not None:
                embeddings.append(embedding)
                total_embeddings += 1
                print(" ✅")
            else:
                print(" ❌")

        if embeddings:
            embeddings_array = np.vstack(embeddings).astype(np.float32)
            save_student_embeddings(student_id, student_name, embeddings_array)
            processed_students += 1
            print(f"  💾 Saved {len(embeddings)} embeddings for {student_name}")
        else:
            print(f"  ⚠️  No valid embeddings for {student_name}")

    if args.update_stats:
        update_student_statistics()

    print("\n" + "="*60)
    print("📊 ENCODING SUMMARY")
    print("="*60)
    print(f"👥 Students processed: {processed_students}/{len(student_folders)}")
    print(f"📸 Total images: {total_images}")
    print(f"🎭 Embeddings created: {total_embeddings}")
    print(f"📁 Index entries: {len(index)}")

    if total_embeddings > 0:
        print("\n✅ Encoding completed successfully!")
        return True
    else:
        print("\n❌ No embeddings were created.")
        print("   Check that images contain clear, front-facing faces.")
        return False

# ==================== INTERACTIVE MODE ====================
def interactive_mode():
    """Run in interactive mode"""
    print("\n🎮 INTERACTIVE MODE")
    print("-" * 40)

    if not DATASET_DIR.exists():
        print(f"Creating dataset directory: {DATASET_DIR}")
        DATASET_DIR.mkdir(exist_ok=True)
        print("Add student folders (named by student ID) with face images to this directory.")
        print("Each folder should contain a 'name.txt' file with the student's display name.")
        return

    student_folders = sorted([d for d in DATASET_DIR.iterdir() if d.is_dir()])

    if not student_folders:
        print("No students found in dataset.")
        print("\nExpected structure:")
        print("  dataset/")
        print("  ├── 1/")
        print("  │   ├── name.txt  (contains student name)")
        print("  │   ├── face1.jpg")
        print("  │   └── face2.jpg")
        print("  └── 2/")
        print("      ├── name.txt")
        print("      └── photo1.jpg")
        return

    print(f"Found {len(student_folders)} students:")
    for i, folder in enumerate(student_folders, 1):
        name_file = folder / "name.txt"
        student_name = name_file.read_text(encoding='utf-8').strip() if name_file.exists() else folder.name
        image_count = sum(
            len(list(folder.glob(f'*.{ext}')))
            for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']
        )
        print(f"  {i}. {student_name} (ID: {folder.name}) - {image_count} images")

    index = load_existing_index()
    if index:
        print(f"\nExisting encodings: {len(index)} students")

    print("\nOptions:")
    print("  1. Encode only new students (skip already encoded)")
    print("  2. Force re-encode all students")
    print("  3. View existing encodings")
    print("  4. Exit")

    choice = input("\nSelect option (1-4): ").strip()

    if choice == '1':
        args = argparse.Namespace(force=False, update_stats=True)
        main(args)
    elif choice == '2':
        args = argparse.Namespace(force=True, update_stats=True)
        main(args)
    elif choice == '3':
        if index:
            print("\nExisting encodings:")
            for student_id, info in index.items():
                if isinstance(info, dict):
                    student_name = info["name"]
                    emb_file = info["file"]
                else:
                    student_name = student_id
                    emb_file = info
                emb_path = ENCODINGS_DIR / emb_file
                count = 0
                if emb_path.exists():
                    embeddings = np.load(str(emb_path))
                    count = embeddings.shape[0] if embeddings.ndim > 1 else 1
                print(f"  👤 {student_name} (ID: {student_id}) -> {emb_file} ({count} embeddings)")
        else:
            print("\nNo existing encodings.")
    elif choice == '4':
        print("Exiting...")
    else:
        print("Invalid choice.")

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Encode faces using InsightFace (ID‑based folder structure)"
    )
    parser.add_argument("--force", action="store_true",
                       help="Force re-encoding of all faces (ignore existing encodings)")
    parser.add_argument("--update-stats", action="store_true", default=True,
                       help="Update student statistics in database after encoding")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run in interactive mode")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        success = main(args)
        sys.exit(0 if success else 1)