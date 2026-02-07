import os
import hashlib
from werkzeug.utils import secure_filename
from config import Config


class FileService:
    """Service for handling file operations securely"""
    
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed"""
        ALLOWED_EXTENSIONS = set(Config.ALLOWED_FILE_TYPES)
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @staticmethod
    def generate_secure_filename(filename: str) -> str:
        """Generate a secure filename"""
        return secure_filename(filename)
    
    @staticmethod
    def save_file(file, upload_dir: str, filename: str = None) -> str:
        """Save file to specified directory with optional custom filename"""
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        if filename is None:
            filename = FileService.generate_secure_filename(file.filename)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        return filepath
    
    @staticmethod
    def get_file_hash(filepath: str) -> str:
        """Calculate MD5 hash of file for integrity checking"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    @staticmethod
    def validate_file_size(filepath: str, max_size: int = None) -> bool:
        """Validate file size against maximum allowed size"""
        if max_size is None:
            max_size = Config.FILE_UPLOAD_MAX_SIZE
        
        file_size = os.path.getsize(filepath)
        return file_size <= max_size
    
    @staticmethod
    def delete_file(filepath: str) -> bool:
        """Delete file from filesystem"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False