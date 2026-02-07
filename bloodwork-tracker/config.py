import os
from datetime import timedelta


class Config:
    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-dev-secret-key-change-in-production'
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or '32-character-long-encryption-key-here!'
    
    # Session settings
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME', 3600))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION', 300))
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///bloodwork.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_BACKUP_ENABLED = os.environ.get('DATABASE_BACKUP_ENABLED', 'true').lower() == 'true'
    DATABASE_BACKUP_PATH = os.environ.get('DATABASE_BACKUP_PATH') or './backups'
    DATABASE_BACKUP_RETENTION_DAYS = int(os.environ.get('DATABASE_BACKUP_RETENTION_DAYS', 30))
    
    # File security
    FILE_UPLOAD_MAX_SIZE = int(os.environ.get('FILE_UPLOAD_MAX_SIZE', 20971520))  # 20MB
    ALLOWED_FILE_TYPES = os.environ.get('ALLOWED_FILE_TYPES', 'pdf,jpg,jpeg,png').split(',')
    
    # AI settings
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'mock')  # local, openai, lmstudio, mock
    AI_SEND_TO_CLOUD = os.environ.get('AI_SEND_TO_CLOUD', 'false').lower() == 'true'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama2')
    LMSTUDIO_BASE_URL = os.environ.get('LMSTUDIO_BASE_URL', 'http://localhost:1234')
    
    # Application
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Directories
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    
    @staticmethod
    def init_directories():
        """Initialize required directories"""
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)