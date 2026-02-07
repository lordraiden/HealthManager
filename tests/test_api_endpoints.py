import pytest
import json
from datetime import datetime, date
from app import create_app, db
from app.models import Patient, User
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
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


def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_auth_login_success(client):
    """Test successful login"""
    response = client.post('/api/v1/auth/login',
                          data=json.dumps({
                              'username': 'testuser',
                              'password': 'testpass123'
                          }),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'


def test_auth_login_failure(client):
    """Test failed login"""
    response = client.post('/api/v1/auth/login',
                          data=json.dumps({
                              'username': 'testuser',
                              'password': 'wrongpassword'
                          }),
                          content_type='application/json')
    assert response.status_code == 401


def test_get_patients_unauthorized(client):
    """Test getting patients without authorization"""
    response = client.get('/api/v1/patients')
    assert response.status_code == 401


def test_crud_patients_authorized(client):
    """Test patient CRUD operations with authorization"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test creating a patient
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'John Doe',
                              'birth_date': '1990-05-15',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    data = json.loads(response.data)
    patient_id = data['id']
    assert data['name'] == 'John Doe'
    
    # Test getting the patient
    response = client.get(f'/api/v1/patients/{patient_id}', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == 'John Doe'
    
    # Test updating the patient
    response = client.put(f'/api/v1/patients/{patient_id}',
                         data=json.dumps({
                             'name': 'John Smith',
                             'notes': 'Updated patient'
                         }),
                         content_type='application/json',
                         headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['name'] == 'John Smith'
    
    # Test getting all patients
    response = client.get('/api/v1/patients', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['total'] == 1


def test_fhir_patient_endpoints(client):
    """Test FHIR patient endpoints"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Jane FHIR',
                              'birth_date': '1985-03-20',
                              'gender': 'female'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    fhir_id = patient_data['fhir_id']
    
    # Test FHIR patient endpoint
    response = client.get(f'/fhir/Patient/{fhir_id}', headers=headers)
    assert response.status_code == 200
    fhir_data = json.loads(response.data)
    assert fhir_data['resourceType'] == 'Patient'
    assert fhir_data['name'][0]['text'] == 'Jane FHIR'


def test_analytics_endpoints(client):
    """Test analytics endpoints"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create a patient first
    response = client.post('/api/v1/patients',
                          data=json.dumps({
                              'name': 'Analytics Test',
                              'birth_date': '1990-01-01',
                              'gender': 'male'
                          }),
                          content_type='application/json',
                          headers=headers)
    assert response.status_code == 201
    patient_data = json.loads(response.data)
    patient_id = patient_data['id']
    
    # Test patient summary endpoint
    response = client.get(f'/api/v1/analytics/summary/{patient_id}', headers=headers)
    assert response.status_code == 200
    summary_data = json.loads(response.data)
    assert 'patient' in summary_data
    assert 'analytics' in summary_data
    assert summary_data['patient']['id'] == patient_id
    assert summary_data['patient']['name'] == 'Analytics Test'


def test_backup_endpoints(client):
    """Test backup endpoints"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test list backups endpoint
    response = client.get('/api/v1/backup/list', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_ai_endpoints(client):
    """Test AI endpoints"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test list providers endpoint
    response = client.get('/api/v1/ai/providers', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) > 0
    provider_names = [provider['name'] for provider in data]
    assert 'mock' in provider_names
    assert 'ollama' in provider_names
    assert 'lmstudio' in provider_names
    assert 'openai' in provider_names