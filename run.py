"""
Application Entry Point
"""
import os
import logging
from pathlib import Path
from app import create_app
from app.models.database import init_database

# Create Flask app
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

# Setup logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Initialize database
    logger.info("Initializing database...")
    init_database(app.config['DATABASE_PATH'])
    
    # Print startup info
    print("\n" + "="*60)
    print("AI Attendance System")
    print("="*60)
    print(f"Database: {app.config['DATABASE_PATH']}")
    print(f"Dataset: {app.config['DATASET_DIR']}")
    print(f"Encodings: {app.config['ENCODINGS_DIR']}")
    print("="*60)
    print("Default Credentials:")
    print("   Admin: admin / admin123")
    print("   Teacher: teacher1 / teacher123")
    print("   Student: student1 / student123")
    print("="*60)
    print("Server starting on http://0.0.0.0:4000")
    print("Environment: " + config_name)
    print("="*60 + "\n")
    
    # Run the app
    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=4000
    )