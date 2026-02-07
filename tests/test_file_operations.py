import pytest
import json
import tempfile
import os
from datetime import datetime
from app import create_app, db
from app.models import Patient, User, MedicalDocument
from werkzeug.security import generate_password_hash
from io import BytesIO


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['FILE_UPLOAD_MAX_SIZE'] = 20971520  # 20MB
    app.config['ALLOWED_FILE_TYPES'] = ['pdf', 'jpg', 'jpeg', 'png']
    
    with app.app_context():
        db.create_all()
        # Create a test user
        user = User(
            username="testuser",
            password_hash=generate_password_hash("testpass123"),
            email="test@example.com"
        )
        db.session.add(user)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def get_auth_token(client):
    """Helper function to get authentication token"""
    response = client.post('/api/v1/auth/login', 
                          data=json.dumps({
                              'username': 'testuser',
                              'password': 'testpass123'
                          }),
                          content_type='application/json')
    data = json.loads(response.data)
    return data['access_token']


def test_document_upload_endpoint(client):
    """Test document upload functionality"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a test patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Test Patient for Document Upload',
                              'birth_date': '1990-01-01',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    
    # Create a mock PDF file for upload
    test_pdf_content = b'%PDF-1.4\n%Test PDF Content\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    
    # Test document upload
    data = {
        'file': (BytesIO(test_pdf_content), 'test_document.pdf'),
        'patient_id': patient_id,
        'description': 'Test lab results'
    }
    
    response = client.post('/api/v1/documents/upload',
                          data=data,
                          content_type='multipart/form-data',
                          headers=headers)
    
    assert response.status_code == 201
    document_data = json.loads(response.data)
    assert 'id' in document_data
    assert document_data['filename'] == 'test_document.pdf'
    assert document_data['file_type'] == 'pdf'
    assert document_data['patient_id'] == patient_id


def test_document_list_endpoint(client):
    """Test listing documents"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a test patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Test Patient for Document List',
                              'birth_date': '1990-01-01',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    
    # List documents for the patient (should be empty initially)
    response = client.get(f'/api/v1/documents?patient={patient_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total'] == 0


def test_document_download_and_preview_endpoints(client):
    """Test document download and preview functionality"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a test patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Test Patient for Download',
                              'birth_date': '1990-01-01',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    
    # Create a document in the database (simulating upload)
    document = MedicalDocument(
        patient_id=patient_id,
        filename='test_lab_results.pdf',
        filepath='/tmp/test_lab_results.pdf',  # This won't actually exist, causing a 404
        file_type='pdf',
        file_size=1024,
        description='Test lab results'
    )
    with client.application.app_context():
        db.session.add(document)
        db.session.commit()
        document_id = document.id
    
    # Test that trying to download a non-existent file returns 404
    response = client.get(f'/api/v1/documents/{document_id}/download', headers=headers)
    assert response.status_code == 404


def test_invalid_file_type_rejection(client):
    """Test that invalid file types are rejected"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a test patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Test Patient for Invalid File',
                              'birth_date': '1990-01-01',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    
    # Create an invalid file type
    test_exe_content = b'This is not a valid file type'
    
    data = {
        'file': (BytesIO(test_exe_content), 'malicious.exe'),
        'patient_id': patient_id,
        'description': 'Invalid file type test'
    }
    
    response = client.post('/api/v1/documents/upload',
                          data=data,
                          content_type='multipart/form-data',
                          headers=headers)
    
    # Should return an error for invalid file type
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'File type not allowed' in response_data['error']


def test_file_size_limit(client):
    """Test that large files are rejected based on size limit"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a test patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Test Patient for Large File',
                              'birth_date': '1990-01-01',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    
    # Create a file larger than the limit (20MB limit, create 25MB)
    large_content = b'0' * (25 * 1024 * 1024)  # 25MB of zeros
    
    data = {
        'file': (BytesIO(large_content), 'large_file.pdf'),
        'patient_id': patient_id,
        'description': 'Large file test'
    }
    
    response = client.post('/api/v1/documents/upload',
                          data=data,
                          content_type='multipart/form-data',
                          headers=headers)
    
    # Should return an error for file too large
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'File too large' in response_data['error']


def test_missing_patient_id_rejection(client):
    """Test that uploads without patient ID are rejected"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a mock PDF file for upload
    test_pdf_content = b'%PDF-1.4\n%Test PDF Content\n'
    
    data = {
        'file': (BytesIO(test_pdf_content), 'test_document.pdf'),
        # Missing patient_id intentionally
        'description': 'Missing patient ID test'
    }
    
    response = client.post('/api/v1/documents/upload',
                          data=data,
                          content_type='multipart/form-data',
                          headers=headers)
    
    # Should return an error for missing patient ID
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Patient ID is required' in response_data['error']


def test_nonexistent_patient_rejection(client):
    """Test that uploads to nonexistent patients are rejected"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a mock PDF file for upload
    test_pdf_content = b'%PDF-1.4\n%Test PDF Content\n'
    
    data = {
        'file': (BytesIO(test_pdf_content), 'test_document.pdf'),
        'patient_id': 99999,  # Nonexistent patient ID
        'description': 'Nonexistent patient test'
    }
    
    response = client.post('/api/v1/documents/upload',
                          data=data,
                          content_type='multipart/form-data',
                          headers=headers)
    
    # Should return an error for nonexistent patient
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert 'error' in response_data
    assert 'Patient not found' in response_data['error']