import os
import shutil
import zipfile
import glob
from datetime import datetime
from config import Config


class BackupService:
    """Service for handling database and file backups"""
    
    @staticmethod
    def create_backup(backup_dir: str = None) -> str:
        """Create a backup of the database and documents"""
        if backup_dir is None:
            backup_dir = Config.DATABASE_BACKUP_PATH
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bloodwork_backup_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create a zip file with the database and documents
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Add database file
            if os.path.exists('bloodwork.db'):
                backup_zip.write('bloodwork.db', 'database/bloodwork.db')
            
            # Add documents directory if it exists
            if os.path.exists('data'):
                for root, dirs, files in os.walk('data'):
                    for file in files:
                        file_path = os.path.join(root, file)
                        archive_path = os.path.relpath(file_path, '.')
                        backup_zip.write(file_path, f"documents/{archive_path}")
        
        return backup_path
    
    @staticmethod
    def list_backups(backup_dir: str = None) -> list:
        """List all available backups"""
        if backup_dir is None:
            backup_dir = Config.DATABASE_BACKUP_PATH
        
        backup_files = glob.glob(os.path.join(backup_dir, "bloodwork_backup_*.zip"))
        backups = []
        
        for backup_file in backup_files:
            filename = os.path.basename(backup_file)
            stat = os.stat(backup_file)
            backups.append({
                'filename': filename,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': backup_file
            })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return backups
    
    @staticmethod
    def restore_backup(backup_filename: str, backup_dir: str = None) -> bool:
        """Restore from a backup file"""
        if backup_dir is None:
            backup_dir = Config.DATABASE_BACKUP_PATH
        
        backup_path = os.path.join(backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Extract the backup
        extract_path = os.path.join(backup_dir, "temp_restore")
        os.makedirs(extract_path, exist_ok=True)
        
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            backup_zip.extractall(extract_path)
        
        # Restore database
        db_path = os.path.join(extract_path, 'database', 'bloodwork.db')
        if os.path.exists(db_path):
            # Remove the current database file
            if os.path.exists('bloodwork.db'):
                os.remove('bloodwork.db')
            
            # Move the restored database to the right location
            shutil.move(db_path, 'bloodwork.db')
        
        # Restore documents
        docs_path = os.path.join(extract_path, 'documents')
        if os.path.exists(docs_path):
            # Remove the current data directory
            if os.path.exists('data'):
                shutil.rmtree('data')
            
            # Move the restored documents to the right location
            shutil.move(docs_path, 'data')
        
        # Clean up temp directory
        shutil.rmtree(extract_path)
        
        return True
    
    @staticmethod
    def delete_old_backups(backup_dir: str = None, days_to_keep: int = None) -> int:
        """Delete backups older than specified days"""
        if backup_dir is None:
            backup_dir = Config.DATABASE_BACKUP_PATH
        
        if days_to_keep is None:
            days_to_keep = Config.DATABASE_BACKUP_RETENTION_DAYS
        
        import time
        current_time = time.time()
        cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
        
        backup_files = glob.glob(os.path.join(backup_dir, "bloodwork_backup_*.zip"))
        deleted_count = 0
        
        for backup_file in backup_files:
            file_modified = os.path.getmtime(backup_file)
            if file_modified < cutoff_time:
                os.remove(backup_file)
                deleted_count += 1
        
        return deleted_count