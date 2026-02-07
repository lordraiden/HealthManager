from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from config import Config
import os
import shutil
import zipfile
import sqlite3
from datetime import datetime
from app.schemas import BackupCreateRequest, BackupResponse
import glob

bp = Blueprint('backup', __name__, url_prefix='/api/v1/backup')


@bp.route('/create', methods=['POST'])
@jwt_required()
def create_backup():
    """Create a backup of the database and documents"""
    try:
        data = request.get_json()
        req = BackupCreateRequest(**data) if data else BackupCreateRequest()
        
        # Create backup directory if it doesn't exist
        backup_dir = Config.DATABASE_BACKUP_PATH
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = req.name or f"backup_{timestamp}"
        backup_filename = f"{backup_name}_{timestamp}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create a zip file with database and documents
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Add database file to backup
            db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
            if os.path.exists(db_path):
                backup_zip.write(db_path, os.path.basename(db_path))
            
            # Add data directory (with patient documents) to backup
            data_dir = os.path.join('app', 'data')
            if os.path.exists(data_dir):
                for root, dirs, files in os.walk(data_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        archive_path = os.path.relpath(file_path, os.path.dirname(data_dir))
                        backup_zip.write(file_path, archive_path)
        
        # Get file size
        file_size = os.path.getsize(backup_path)
        
        # Clean up old backups based on retention policy
        cleanup_old_backups()
        
        backup_response = BackupResponse(
            id=backup_filename,
            name=backup_name,
            size=file_size,
            created_at=datetime.now(),
            path=backup_path
        )
        
        return jsonify(backup_response.dict()), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_backups():
    """List all available backups"""
    try:
        backup_dir = Config.DATABASE_BACKUP_PATH
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        
        # Find all backup files
        backup_pattern = os.path.join(backup_dir, "*.zip")
        backup_files = glob.glob(backup_pattern)
        
        backups = []
        for backup_path in backup_files:
            filename = os.path.basename(backup_path)
            stat = os.stat(backup_path)
            
            # Try to extract name and date from filename
            name_parts = filename.split('_')
            if len(name_parts) >= 3 and name_parts[-1].endswith('.zip'):
                # Format: name_timestamp.zip
                backup_name = '_'.join(name_parts[:-2])
                date_str = name_parts[-2]
                time_str = name_parts[-1].replace('.zip', '')
            else:
                backup_name = filename.replace('.zip', '')
                date_str = ''
                time_str = ''
            
            try:
                # Parse date from filename if possible
                created_at = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except ValueError:
                # If parsing fails, use file modification time
                created_at = datetime.fromtimestamp(stat.st_mtime)
            
            backup_response = BackupResponse(
                id=filename,
                name=backup_name,
                size=stat.st_size,
                created_at=created_at,
                path=backup_path
            )
            
            backups.append(backup_response.dict())
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify(backups), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/restore', methods=['POST'])
@jwt_required()
def restore_backup():
    """Restore from a backup"""
    try:
        data = request.get_json()
        backup_id = data.get('backup_id')
        
        if not backup_id:
            return jsonify({'error': 'Backup ID is required'}), 400
        
        backup_dir = Config.DATABASE_BACKUP_PATH
        backup_path = os.path.join(backup_dir, backup_id)
        
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        # Close all database connections before restoring
        db.engine.dispose()
        
        # Extract the backup
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            # Extract to a temporary location first
            temp_extract_dir = os.path.join(backup_dir, 'temp_restore')
            backup_zip.extractall(temp_extract_dir)
            
            # Replace the current database and data files
            extracted_db_path = os.path.join(temp_extract_dir, os.path.basename(Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')))
            if os.path.exists(extracted_db_path):
                # Stop any active connections and replace the database
                current_db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
                if os.path.exists(current_db_path):
                    os.remove(current_db_path)
                shutil.move(extracted_db_path, current_db_path)
            
            # Restore data directory
            extracted_data_dir = os.path.join(temp_extract_dir, 'data')
            if os.path.exists(extracted_data_dir):
                current_data_dir = os.path.join('app', 'data')
                if os.path.exists(current_data_dir):
                    shutil.rmtree(current_data_dir)
                shutil.move(extracted_data_dir, current_data_dir)
        
        # Clean up temp directory
        temp_extract_dir = os.path.join(backup_dir, 'temp_restore')
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
        
        return jsonify({'message': 'Backup restored successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<backup_id>', methods=['DELETE'])
@jwt_required()
def delete_backup(backup_id):
    """Delete a specific backup"""
    try:
        backup_dir = Config.DATABASE_BACKUP_PATH
        backup_path = os.path.join(backup_dir, backup_id)
        
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        os.remove(backup_path)
        
        return jsonify({'message': 'Backup deleted successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def cleanup_old_backups():
    """Remove backups older than the retention period"""
    try:
        backup_dir = Config.DATABASE_BACKUP_PATH
        if not os.path.exists(backup_dir):
            return
        
        # Get all backup files sorted by modification time (oldest first)
        backup_pattern = os.path.join(backup_dir, "*.zip")
        backup_files = glob.glob(backup_pattern)
        backup_files.sort(key=os.path.getmtime)
        
        # Calculate cutoff date
        retention_days = Config.DATABASE_BACKUP_RETENTION_DAYS
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        
        # Remove old backups
        removed_count = 0
        for backup_file in backup_files:
            if os.path.getmtime(backup_file) < cutoff_time:
                os.remove(backup_file)
                removed_count += 1
        
        print(f"Cleaned up {removed_count} old backups")
    except Exception as e:
        print(f"Error cleaning up old backups: {str(e)}")