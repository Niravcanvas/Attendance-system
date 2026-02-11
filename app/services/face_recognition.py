"""
Face Recognition Service using InsightFace
"""
import numpy as np
import cv2
from functools import lru_cache
import json
from pathlib import Path

try:
    import insightface
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("WARNING: InsightFace not installed. Install with: pip install insightface")


class FaceRecognitionService:
    """Service for face detection and recognition"""
    
    def __init__(self, config):
        self.config = config
        self.app = None
        self.model = None
        self.initialized = False
        
    def initialize(self):
        """Initialize InsightFace models"""
        if not INSIGHTFACE_AVAILABLE:
            print("ERROR: InsightFace not available")
            return False
        
        try:
            print("Initializing InsightFace...")
            
            # Initialize FaceAnalysis for detection
            self.app = FaceAnalysis(
                name=self.config.FACE_MODEL_NAME,
                providers=self.config.FACE_PROVIDERS
            )
            self.app.prepare(ctx_id=0, det_size=self.config.DETECTION_SIZE)
            
            # Load recognition model for embeddings
            self.model = get_model(self.config.FACE_MODEL_NAME, download=True)
            self.model.prepare(ctx_id=0)
            
            self.initialized = True
            print("✅ InsightFace initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize InsightFace: {e}")
            return False
    
    def detect_faces(self, image_array):
        """Detect faces in image using InsightFace"""
        if not self.initialized or not self.app:
            return []
        
        try:
            # Convert image to RGB if needed
            if len(image_array.shape) == 2:  # Grayscale
                image_array = cv2.cvtColor(image_array, cv2.COLOR_GRAY2RGB)
            elif image_array.shape[2] == 4:  # RGBA
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2RGB)
            
            # Detect faces
            faces = self.app.get(image_array)
            
            results = []
            for face in faces:
                bbox = face.bbox.astype(int)
                landmarks = face.kps if hasattr(face, 'kps') else []
                
                results.append({
                    'bbox': bbox.tolist(),
                    'landmarks': landmarks.tolist() if len(landmarks) > 0 else [],
                    'det_score': float(face.det_score),
                    'embedding': face.normed_embedding.tolist() if hasattr(face, 'normed_embedding') else None
                })
            
            return results
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def extract_embedding(self, image_array, bbox):
        """Extract face embedding from bounding box"""
        if not self.initialized or not self.model:
            return None
        
        try:
            x1, y1, x2, y2 = bbox
            # Ensure valid bounding box
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image_array.shape[1], x2), min(image_array.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            face_img = image_array[y1:y2, x1:x2]
            if face_img.size == 0:
                return None
            
            embedding = self.model.get_feat(face_img)
            if embedding is not None:
                # Normalize embedding
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            
            return None
        except Exception as e:
            print(f"Error extracting embedding: {e}")
            return None
    
    @staticmethod
    def cosine_similarity(a, b):
        """Calculate cosine similarity between vector a and matrix b"""
        if b.size == 0:
            return np.array([])
        
        a_norm = a / (np.linalg.norm(a) + 1e-10)
        b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
        
        return np.dot(b_norm, a_norm).flatten()
    
    def load_all_embeddings(self, index_file, encodings_dir):
        """Load all face embeddings from index"""
        if not Path(index_file).exists():
            return [], np.zeros((0, 512), dtype=np.float32)
        
        try:
            with open(index_file, 'r') as f:
                index = json.load(f)
            
            all_names = []
            all_embeddings = []
            
            for name, emb_file in index.items():
                emb_path = Path(encodings_dir) / emb_file
                if emb_path.exists():
                    embeddings = np.load(str(emb_path))
                    if embeddings.ndim == 1:
                        embeddings = embeddings.reshape(1, -1)
                    
                    all_names.extend([name] * embeddings.shape[0])
                    all_embeddings.append(embeddings)
            
            if all_embeddings:
                all_embeddings = np.vstack(all_embeddings)
            else:
                all_embeddings = np.zeros((0, 512), dtype=np.float32)
            
            return all_names, all_embeddings
        except Exception as e:
            print(f"Error loading embeddings: {e}")
            return [], np.zeros((0, 512), dtype=np.float32)
    
    def save_student_embeddings(self, student_name, embeddings, encodings_dir, index_file):
        """Save embeddings for a student"""
        from werkzeug.utils import secure_filename
        
        try:
            # Save embeddings file
            emb_filename = f"{secure_filename(student_name)}.npy"
            emb_path = Path(encodings_dir) / emb_filename
            np.save(str(emb_path), embeddings.astype(np.float32))
            
            # Update index
            index = {}
            if Path(index_file).exists():
                with open(index_file, 'r') as f:
                    index = json.load(f)
            
            index[student_name] = emb_filename
            
            with open(index_file, 'w') as f:
                json.dump(index, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving embeddings: {e}")
            return False
    
    def recognize_faces(self, image_path, index_file, encodings_dir, threshold=0.5):
        """Recognize faces in an image and return results"""
        import base64
        from datetime import datetime
        
        if not self.initialized:
            return {"error": "InsightFace not initialized", "success": False}
        
        # Load embeddings
        names_db, vecs_db = self.load_all_embeddings(index_file, encodings_dir)
        if vecs_db.size == 0:
            return {"error": "No embeddings found", "success": False}
        
        # Read image
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            return {"error": "Failed to read image", "success": False}
        
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = self.detect_faces(img_rgb)
        
        # Annotate image
        annotated = img_bgr.copy()
        recognitions = []
        marked_count = 0
        
        for face in faces:
            bbox = face['bbox']
            x1, y1, x2, y2 = bbox
            
            # Get embedding
            if face.get('embedding'):
                emb = np.array(face['embedding'])
            else:
                emb = self.extract_embedding(img_rgb, bbox)
            
            name = "Unknown"
            confidence = 0.0
            
            if emb is not None and vecs_db.size > 0:
                similarities = self.cosine_similarity(emb, vecs_db)
                if similarities.size > 0:
                    best_idx = np.argmax(similarities)
                    best_sim = similarities[best_idx]
                    
                    if best_sim >= threshold:
                        name = names_db[best_idx]
                        confidence = float(best_sim)
                        marked_count += 1
            
            # Draw bounding box
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{name} ({confidence:.2f})"
            cv2.putText(annotated, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            recognitions.append({
                "name": name,
                "confidence": confidence,
                "bbox": bbox,
                "landmarks": face.get('landmarks', [])
            })
        
        # Save annotated image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = Path(image_path).stem
        
        # Clean original name
        clean_name = original_name
        while clean_name.startswith('annotated_'):
            clean_name = clean_name[10:]
        
        annotated_filename = f"annotated_{clean_name}_{timestamp}.jpg"
        uploads_dir = Path(image_path).parent
        annotated_path = uploads_dir / annotated_filename
        
        cv2.imwrite(str(annotated_path), annotated)
        
        # Convert to base64
        _, buffer = cv2.imencode('.jpg', annotated)
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "success": True,
            "faces_found": len(faces),
            "recognized": marked_count,
            "recognitions": recognitions,
            "annotated_image": f"data:image/jpeg;base64,{annotated_base64}",
            "annotated_path": str(annotated_path),
            "annotated_filename": annotated_filename
        }