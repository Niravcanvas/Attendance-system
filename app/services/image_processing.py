"""
Image Processing Utilities
"""
from PIL import Image
from pathlib import Path


def save_thumbnail(image_path, thumb_dir, max_size=320):
    """Create thumbnail for an image and return relative URL"""
    try:
        img = Image.open(str(image_path)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        thumb_name = f"thumb_{Path(image_path).name}"
        thumb_path = Path(thumb_dir) / thumb_name
        img.save(str(thumb_path), "JPEG", quality=85)
        
        return f"uploads/thumbs/{thumb_name}"
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def cleanup_old_files(directory, max_files=20, pattern='annotated_*.jpg'):
    """Keep only recent files matching pattern"""
    try:
        files = list(Path(directory).glob(pattern))
        
        if len(files) > max_files:
            # Sort by modification time (oldest first)
            files.sort(key=lambda x: x.stat().st_mtime)
            
            # Delete old files
            for file in files[:-max_files]:
                file.unlink()
                print(f"Cleaned up old file: {file.name}")
    
    except Exception as e:
        print(f"Error cleaning up files: {e}")