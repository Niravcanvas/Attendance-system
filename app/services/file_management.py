"""
File Management Service
"""
import json
from datetime import datetime
from pathlib import Path


def append_to_timeline(timeline_file, photo_name, marked_count, total_faces, subject="", teacher=""):
    """Add entry to timeline JSON"""
    try:
        timeline = []
        if Path(timeline_file).exists():
            with open(timeline_file, 'r') as f:
                timeline = json.load(f)
        
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "photo": photo_name,
            "marked": marked_count,
            "faces_found": total_faces,
            "subject": subject,
            "teacher": teacher
        }
        
        timeline.insert(0, entry)
        # Keep only last 100 entries
        timeline = timeline[:100]
        
        with open(timeline_file, 'w') as f:
            json.dump(timeline, f, indent=2)
    except Exception as e:
        print(f"Error updating timeline: {e}")


def get_storage_size(directory):
    """Calculate total storage used in a directory"""
    total_size = 0
    for file in Path(directory).rglob('*'):
        if file.is_file():
            total_size += file.stat().st_size
    return total_size