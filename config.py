import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or '32-character-encryption-key-here!'
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.environ.get('SESSION_LIFETIME', 3600)))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION', 300))  # seconds
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///bloodwork.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_BACKUP_ENABLED = os.environ.get('DATABASE_BACKUP_ENABLED', 'true').lower() == 'true'
    DATABASE_BACKUP_PATH = os.environ.get('DATABASE_BACKUP_PATH') or './backups'
    DATABASE_BACKUP_RETENTION_DAYS = int(os.environ.get('DATABASE_BACKUP_RETENTION_DAYS', 30))
    
    # File uploads
    FILE_UPLOAD_MAX_SIZE = int(os.environ.get('FILE_UPLOAD_MAX_SIZE', 20971520))  # 20MB default
    ALLOWED_FILE_TYPES = os.environ.get('ALLOWED_FILE_TYPES', 'pdf,jpg,jpeg,png').split(',')
    
    # AI settings
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'mock')  # local, openai, lmstudio, mock
    AI_SEND_TO_CLOUD = os.environ.get('AI_SEND_TO_CLOUD', 'false').lower() == 'true'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama2')
    LMSTUDIO_BASE_URL = os.environ.get('LMSTUDIO_BASE_URL', 'http://localhost:1234')
    
    # Application
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Maximum number of patient profiles allowed
    MAX_PATIENT_PROFILES = 4