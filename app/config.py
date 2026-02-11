"""
Configuration settings for the Attendance System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent.absolute()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Database
    DATABASE_PATH = BASE_DIR / 'data' / 'database' / 'attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Directories
    DATASET_DIR = BASE_DIR / 'data' / 'dataset'
    ENCODINGS_DIR = BASE_DIR / 'data' / 'encodings'
    UPLOADS_DIR = BASE_DIR / 'data' / 'uploads'
    FACES_DIR = UPLOADS_DIR / 'faces'
    THUMBS_DIR = UPLOADS_DIR / 'thumbs'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG'}
    
    # Face Recognition
    RECOGNITION_THRESHOLD = 0.5  # Minimum similarity for recognition
    REVERIFY_THRESHOLD = 0.6     # Higher threshold for re-verification
    DETECTION_SIZE = (640, 640)  # Face detection input size
    
    # InsightFace
    FACE_MODEL_NAME = 'buffalo_l'
    FACE_PROVIDERS = ['CPUExecutionProvider']
    
    # Session
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Management
    MAX_RECENT_CAPTURES = 20  # Keep only recent captures
    THUMBNAIL_SIZE = 320
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Create directories
        directories = [
            Config.DATASET_DIR,
            Config.ENCODINGS_DIR,
            Config.UPLOADS_DIR,
            Config.FACES_DIR,
            Config.THUMBS_DIR,
            Config.LOGS_DIR,
            Config.DATABASE_PATH.parent
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Override in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        assert cls.SECRET_KEY, 'SECRET_KEY must be set in production!'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = BASE_DIR / 'data' / 'database' / 'test_attendance.db'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}