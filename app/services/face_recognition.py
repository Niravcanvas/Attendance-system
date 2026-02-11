"""
Face Recognition Service using InsightFace
"""
import numpy as np
import cv2
import json
from pathlib import Path

try:
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("WARNING: InsightFace not installed. Install with: pip install insightface")


class FaceRecognitionService:
    """Service for face detection and recognition"""

    def __init__(self, config):
        # config = app.config (Flask dict-like config)
        self.config = config
        self.app = None
        self.model = None
        self.initialized = False

    # --------------------------------------------------

    def initialize(self):
        """Initialize InsightFace models"""
        if not INSIGHTFACE_AVAILABLE:
            print("ERROR: InsightFace not available")
            return False

        try:
            print("Initializing InsightFace...")

            model_name = self.config.get("FACE_MODEL_NAME", "buffalo_l")
            providers = self.config.get("FACE_PROVIDERS", ["CPUExecutionProvider"])
            det_size = self.config.get("DETECTION_SIZE", (640, 640))

            # Detection + embedding pipeline
            self.app = FaceAnalysis(
                name=model_name,
                providers=providers
            )
            self.app.prepare(ctx_id=0, det_size=det_size)

            # Recognition model
            self.model = get_model(model_name, download=True)
            self.model.prepare(ctx_id=0)

            self.initialized = True
            print("✅ InsightFace initialized successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize InsightFace: {e}")
            return False

    # --------------------------------------------------

    def detect_faces(self, image_array):
        if not self.initialized or not self.app:
            return []

        try:
            if len(image_array.shape) == 2:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
            elif image_array.shape[2] == 4:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)

            faces = self.app.get(image_array)

            results = []
            for face in faces:
                bbox = face.bbox.astype(int)
                landmarks = face.kps if hasattr(face, "kps") else []

                results.append({
                    "bbox": bbox.tolist(),
                    "landmarks": landmarks.tolist() if len(landmarks) > 0 else [],
                    "det_score": float(face.det_score),
                    "embedding": face.normed_embedding.tolist()
                    if hasattr(face, "normed_embedding") else None
                })

            return results

        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []

    # --------------------------------------------------

    def extract_embedding(self, image_array, bbox):
        if not self.initialized or not self.model:
            return None

        try:
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, x1), max(0, y1)
            x2 = min(image_array.shape[1], x2)
            y2 = min(image_array.shape[0], y2)

            if x2 <= x1 or y2 <= y1:
                return None

            face_img = image_array[y1:y2, x1:x2]
            if face_img.size == 0:
                return None

            emb = self.model.get_feat(face_img)
            if emb is not None:
                emb = emb / (np.linalg.norm(emb) + 1e-10)
                return emb

            return None

        except Exception as e:
            print(f"Error extracting embedding: {e}")
            return None

    # --------------------------------------------------

    @staticmethod
    def cosine_similarity(a, b):
        if b.size == 0:
            return np.array([])

        a_norm = a / (np.linalg.norm(a) + 1e-10)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)

        return np.dot(b_norm, a_norm).flatten()

    # --------------------------------------------------

    def load_all_embeddings(self, index_file, encodings_dir):
        if not Path(index_file).exists():
            return [], np.zeros((0, 512), dtype=np.float32)

        try:
            with open(index_file) as f:
                index = json.load(f)

            names = []
            vectors = []

            for name, emb_file in index.items():
                p = Path(encodings_dir) / emb_file
                if p.exists():
                    arr = np.load(str(p))
                    if arr.ndim == 1:
                        arr = arr.reshape(1, -1)

                    names.extend([name] * arr.shape[0])
                    vectors.append(arr)

            if vectors:
                vectors = np.vstack(vectors)
            else:
                vectors = np.zeros((0, 512), dtype=np.float32)

            return names, vectors

        except Exception as e:
            print(f"Error loading embeddings: {e}")
            return [], np.zeros((0, 512), dtype=np.float32)

    # --------------------------------------------------

    def save_student_embeddings(self, student_name, embeddings, encodings_dir, index_file):
        from werkzeug.utils import secure_filename

        try:
            fname = f"{secure_filename(student_name)}.npy"
            path = Path(encodings_dir) / fname
            np.save(str(path), embeddings.astype(np.float32))

            index = {}
            if Path(index_file).exists():
                with open(index_file) as f:
                    index = json.load(f)

            index[student_name] = fname

            with open(index_file, "w") as f:
                json.dump(index, f, indent=2)

            return True

        except Exception as e:
            print(f"Error saving embeddings: {e}")
            return False

    # --------------------------------------------------

    def recognize_faces(self, image_path, index_file, encodings_dir, threshold=0.5):
        import base64
        from datetime import datetime

        if not self.initialized:
            return {"success": False, "error": "InsightFace not initialized"}

        names_db, vecs_db = self.load_all_embeddings(index_file, encodings_dir)
        if vecs_db.size == 0:
            return {"success": False, "error": "No embeddings found"}

        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            return {"success": False, "error": "Failed to read image"}

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        faces = self.detect_faces(img_rgb)

        annotated = img_bgr.copy()
        recognitions = []
        marked = 0

        for face in faces:
            x1, y1, x2, y2 = face["bbox"]

            emb = np.array(face["embedding"]) if face.get("embedding") else self.extract_embedding(img_rgb, face["bbox"])

            name = "Unknown"
            conf = 0.0

            if emb is not None:
                sims = self.cosine_similarity(emb, vecs_db)
                if sims.size > 0:
                    idx = np.argmax(sims)
                    if sims[idx] >= threshold:
                        name = names_db[idx]
                        conf = float(sims[idx])
                        marked += 1

            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                f"{name} ({conf:.2f})",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

            recognitions.append({
                "name": name,
                "confidence": conf,
                "bbox": face["bbox"],
                "landmarks": face.get("landmarks", [])
            })

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"annotated_{Path(image_path).stem}_{ts}.jpg"
        out_path = Path(image_path).parent / out_name

        cv2.imwrite(str(out_path), annotated)

        _, buf = cv2.imencode(".jpg", annotated)
        b64 = base64.b64encode(buf).decode()

        return {
            "success": True,
            "faces_found": len(faces),
            "recognized": marked,
            "recognitions": recognitions,
            "annotated_image": f"data:image/jpeg;base64,{b64}",
            "annotated_path": str(out_path),
            "annotated_filename": out_name
        }