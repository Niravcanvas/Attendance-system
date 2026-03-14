# config.py
import os
from pathlib import Path
from datetime import timedelta


class Config:
    # Base
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

    # Paths
    BASE_DIR = Path(__file__).parent.absolute()
    DATABASE_PATH = BASE_DIR / 'attendance.db'

    # File Uploads
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 50MB
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    DATASET_FOLDER = BASE_DIR / 'dataset'
    ENCODINGS_FOLDER = BASE_DIR / 'encodings'

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG'}

    # Face Recognition
    INSIGHTFACE_MODEL = os.environ.get('INSIGHTFACE_MODEL', 'buffalo_l')
    USE_CUDA = os.environ.get('USE_CUDA', 'false').lower() == 'true'
    RECOGNITION_THRESHOLD = float(os.environ.get('RECOGNITION_THRESHOLD', 0.5))

    # Session Security
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.environ.get('SESSION_LIFETIME_MINUTES', 43200))
    )

    # Server
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / 'logs' / 'app.log'

    # App Info
    APP_NAME = "AI Attendance System"
    APP_VERSION = "1.0.0"

    @classmethod
    def setup_directories(cls):
        """Create required directories if they don't exist."""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.UPLOAD_FOLDER / 'faces',
            cls.UPLOAD_FOLDER / 'thumbs',
            cls.DATASET_FOLDER,
            cls.ENCODINGS_FOLDER,
            cls.BASE_DIR / 'logs',
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate_config(cls):
        """Return a list of warnings about the current config."""
        issues = []
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            issues.append("⚠️  Using default SECRET_KEY — change this in production!")
        if cls.FLASK_ENV == 'production' and cls.DEBUG:
            issues.append("⚠️  DEBUG is enabled in production!")
        return issues


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = 'WARNING'


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATABASE_PATH = ':memory:'
    SECRET_KEY = 'testing-secret-key'
    LOG_LEVEL = 'ERROR'


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return {
        'development': DevelopmentConfig,
        'production':  ProductionConfig,
        'testing':     TestingConfig,
    }.get(env, DevelopmentConfig)


current_config = get_config()