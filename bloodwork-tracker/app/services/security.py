from cryptography.fernet import Fernet
from config import Config
import hashlib
import os


class SecurityService:
    """Service for handling encryption and security operations"""
    
    def __init__(self):
        # Initialize cipher with the configured encryption key
        # Ensure the key is properly formatted (32 bytes for Fernet)
        key = Config.ENCRYPTION_KEY
        if len(key) < 32:
            # Pad the key if it's too short
            key = key.ljust(32, '_')
        elif len(key) > 32:
            # Truncate the key if it's too long
            key = key[:32]
        
        # Convert to bytes and encode in URL-safe base64 format
        self.cipher_suite = Fernet(self._pad_key_to_base64(key.encode()))
    
    def _pad_key_to_base64(self, key_bytes):
        """Pad or truncate key to 32 bytes and encode in URL-safe base64 format"""
        from base64 import urlsafe_b64encode, urlsafe_b64decode
        
        # Ensure key is exactly 32 bytes
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'_')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        
        # Encode in URL-safe base64 format
        return urlsafe_b64encode(key_bytes)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted_bytes = self.cipher_suite.encrypt(data.encode())
        return encrypted_bytes.decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        decrypted_bytes = self.cipher_suite.decrypt(encrypted_data.encode())
        return decrypted_bytes.decode()
    
    @staticmethod
    def hash_data(data: str) -> str:
        """Create SHA-256 hash of data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def generate_salt(length: int = 32) -> str:
        """Generate random salt for hashing"""
        return os.urandom(length).hex()


class AuditLog:
    """Service for logging security-relevant events"""
    
    @staticmethod
    def log_event(event_type: str, user_id: int = None, details: dict = None, ip_address: str = None):
        """Log an audit event"""
        import json
        from datetime import datetime
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'details': details or {},
            'ip_address': ip_address
        }
        
        # In a real implementation, this would write to a secure log file or database
        print(f"AUDIT LOG: {json.dumps(log_entry)}")  # Placeholder implementation