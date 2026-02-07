from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from app import db
from config import Config
import os
import shutil
import zipfile
import sqlite3
from datetime import datetime
import glob


bp = Blueprint('backup', __name__)


@bp.route('/create', methods=['POST'])
@jwt_required()
def create_backup():
    """Create a backup of the database and documents"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"bloodwork_backup_{timestamp}.zip"
        backup_path = os.path.join(Config.DATABASE_BACKUP_PATH, backup_filename)
        
        # Create backup directory if it doesn't exist
        os.makedirs(Config.DATABASE_BACKUP_PATH, exist_ok=True)
        
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
        
        return jsonify({
            'message': 'Backup created successfully',
            'filename': backup_filename,
            'path': backup_path,
            'size': os.path.getsize(backup_path),
            'created_at': timestamp
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/list', methods=['GET'])
@jwt_required()
def list_backups():
    """List all available backups"""
    try:
        backup_files = glob.glob(os.path.join(Config.DATABASE_BACKUP_PATH, "bloodwork_backup_*.zip"))
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
        
        return jsonify({
            'backups': backups,
            'total': len(backups)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/restore', methods=['POST'])
@jwt_required()
def restore_backup():
    """Restore from a backup file"""
    try:
        data = request.get_json()
        backup_filename = data.get('filename')
        
        if not backup_filename:
            return jsonify({'error': 'Backup filename is required'}), 400
        
        backup_path = os.path.join(Config.DATABASE_BACKUP_PATH, backup_filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        # Extract the backup
        extract_path = os.path.join(Config.DATABASE_BACKUP_PATH, "temp_restore")
        os.makedirs(extract_path, exist_ok=True)
        
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            backup_zip.extractall(extract_path)
        
        # Stop any ongoing database operations
        db.session.close()
        
        # Restore database
        db_path = os.path.join(extract_path, 'database', 'bloodwork.db')
        if os.path.exists(db_path):
            # Close the current database connection
            db.engine.dispose()
            
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
        
        # Reinitialize the database connection
        db.create_all()
        
        return jsonify({
            'message': 'Backup restored successfully',
            'restored_file': backup_filename
        }), 200
    
    except Exception as e:
        # Clean up temp directory if something went wrong
        temp_path = os.path.join(Config.DATABASE_BACKUP_PATH, "temp_restore")
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        return jsonify({'error': str(e)}), 500


@bp.route('/download/<filename>', methods=['GET'])
@jwt_required()
def download_backup(filename):
    """Download a specific backup file"""
    try:
        backup_path = os.path.join(Config.DATABASE_BACKUP_PATH, filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        if not filename.startswith('bloodwork_backup_') or not filename.endswith('.zip'):
            return jsonify({'error': 'Invalid backup file'}), 400
        
        return send_file(backup_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/delete/<filename>', methods=['DELETE'])
@jwt_required()
def delete_backup(filename):
    """Delete a specific backup file"""
    try:
        backup_path = os.path.join(Config.DATABASE_BACKUP_PATH, filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404
        
        if not filename.startswith('bloodwork_backup_') or not filename.endswith('.zip'):
            return jsonify({'error': 'Invalid backup file'}), 400
        
        os.remove(backup_path)
        
        return jsonify({
            'message': 'Backup deleted successfully',
            'deleted_file': filename
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500