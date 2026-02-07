import pytest
from app import create_app, db
from app.models import User
from app.services.security import SecurityService


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    
    # Create temporary database
    import tempfile
    import os
    _, temp_db = tempfile.mkstemp(suffix='.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['ENCRYPTION_KEY'] = 'test-encryption-key-32-chars!!'
    
    with app.app_context():
        db.create_all()
        yield app
        
        # Clean up
        db.drop_all()
    os.unlink(temp_db)


class TestSecurityService:
    def test_encryption_decryption(self, app):
        """Test that data can be encrypted and decrypted successfully"""
        with app.app_context():
            security_service = SecurityService()
            
            original_data = "This is sensitive data that needs encryption"
            
            # Encrypt the data
            encrypted_data = security_service.encrypt_data(original_data)
            
            # Verify that encrypted data is different from original
            assert encrypted_data != original_data
            assert isinstance(encrypted_data, str)
            assert len(encrypted_data) > 0
            
            # Decrypt the data
            decrypted_data = security_service.decrypt_data(encrypted_data)
            
            # Verify that decrypted data matches original
            assert decrypted_data == original_data
    
    def test_multiple_encryptions_different(self, app):
        """Test that multiple encryptions of same data produce different results"""
        with app.app_context():
            security_service = SecurityService()
            
            original_data = "Same data to encrypt multiple times"
            
            encrypted_1 = security_service.encrypt_data(original_data)
            encrypted_2 = security_service.encrypt_data(original_data)
            
            # Each encryption should produce a different result due to randomization
            assert encrypted_1 != encrypted_2
            assert encrypted_1 != original_data
            assert encrypted_2 != original_data
    
    def test_hashing(self, app):
        """Test data hashing functionality"""
        with app.app_context():
            original_data = "Data to hash"
            hashed_data = SecurityService.hash_data(original_data)
            
            # Hash should be deterministic for the same input
            same_hash = SecurityService.hash_data(original_data)
            assert hashed_data == same_hash
            
            # Different input should produce different hash
            different_hash = SecurityService.hash_data("Different data")
            assert hashed_data != different_hash
            
            # Hash should be of appropriate length (SHA-256 produces 64 hex chars)
            assert len(hashed_data) == 64
    
    def test_salt_generation(self, app):
        """Test salt generation"""
        with app.app_context():
            salt1 = SecurityService.generate_salt()
            salt2 = SecurityService.generate_salt()
            
            # Salts should be of specified length (default 32 chars = 64 hex chars)
            assert len(salt1) == 64
            assert len(salt2) == 64
            
            # Two salts should be different
            assert salt1 != salt2


class TestUserSecurity:
    def test_password_hashing(self, app):
        """Test that passwords are properly hashed and verified"""
        with app.app_context():
            user = User(username='testuser')
            plaintext_password = 'secretpassword123'
            
            # Set password (should hash it)
            user.set_password(plaintext_password)
            
            # Verify password works
            assert user.check_password(plaintext_password) == True
            
            # Verify wrong password doesn't work
            assert user.check_password('wrongpassword') == False
            
            # Verify original password is not stored in plain text
            assert user.password_hash != plaintext_password
            assert len(user.password_hash) > len(plaintext_password)
    
    def test_password_verification_consistency(self, app):
        """Test that password verification is consistent"""
        with app.app_context():
            user = User(username='testuser')
            password = 'consistent_password_test'
            
            # Set password multiple times to ensure consistency
            user.set_password(password)
            first_hash = user.password_hash
            
            # Verify it works
            assert user.check_password(password) == True
            assert user.check_password('different_password') == False
            
            # Set same password again (should create different hash due to salt)
            user.set_password(password)
            second_hash = user.password_hash
            
            # Different hashes but both should verify correctly
            assert first_hash != second_hash
            assert user.check_password(password) == True
            assert user.check_password('different_password') == False


class TestSensitiveDataHandling:
    def test_encryption_preserves_data_integrity(self, app):
        """Test that encrypted and decrypted data maintains integrity"""
        with app.app_context():
            security_service = SecurityService()
            
            # Test various types of data
            test_cases = [
                "Simple text",
                "Special characters: !@#$%^&*()",
                "Numbers: 123456789",
                "Unicode: áéíóú ñ ç",
                "Long text: " + "A" * 1000,
                "Empty string: ",
                "Mixed: abc123!@#áéí",
                "JSON-like string: {\"key\": \"value\", \"num\": 123}"
            ]
            
            for test_data in test_cases:
                encrypted = security_service.encrypt_data(test_data)
                decrypted = security_service.decrypt_data(encrypted)
                assert decrypted == test_data
    
    def test_encryption_error_handling(self, app):
        """Test error handling in encryption/decryption"""
        with app.app_context():
            security_service = SecurityService()
            
            # Test decryption with invalid data
            with pytest.raises(Exception):
                security_service.decrypt_data("invalid_encrypted_data")
            
            # Test encryption of None
            with pytest.raises(Exception):
                security_service.encrypt_data(None)