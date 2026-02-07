import pytest
import json
from datetime import datetime
from app import create_app, db
from app.models import Patient, User


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
    
    with app.app_context():
        db.create_all()
        
        # Create a test user
        user = User(username='testuser')
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        
        yield app
        
        # Clean up
        db.drop_all()
    os.unlink(temp_db)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'testuser',
        'password': 'testpassword'
    })
    data = response.get_json()
    token = data.get('access_token')
    return {'Authorization': f'Bearer {token}'}


class TestAuthEndpoints:
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'testpassword'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['username'] == 'testuser'
    
    def test_login_failure(self, client):
        """Test failed login"""
        response = client.post('/api/v1/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
    
    def test_protected_route_without_auth(self, client):
        """Test accessing protected route without authentication"""
        response = client.get('/api/v1/patients/')
        assert response.status_code == 401


class TestPatientEndpoints:
    def test_create_patient(self, client, auth_headers):
        """Test creating a patient"""
        patient_data = {
            'name': 'John Doe',
            'birth_date': '1980-05-15',
            'gender': 'male',
            'notes': 'Test patient'
        }
        
        response = client.post('/api/v1/patients/', 
                              json=patient_data, 
                              headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == 'John Doe'
        assert data['gender'] == 'male'
        assert data['notes'] == 'Test patient'
    
    def test_get_patients(self, client, auth_headers):
        """Test getting all patients"""
        # First create a patient
        patient_data = {
            'name': 'Jane Smith',
            'birth_date': '1990-03-20',
            'gender': 'female'
        }
        
        client.post('/api/v1/patients/', 
                   json=patient_data, 
                   headers=auth_headers)
        
        response = client.get('/api/v1/patients/', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'patients' in data
        assert len(data['patients']) >= 1
        assert any(p['name'] == 'Jane Smith' for p in data['patients'])
    
    def test_get_single_patient(self, client, auth_headers):
        """Test getting a single patient"""
        # Create a patient first
        patient_data = {
            'name': 'Bob Johnson',
            'birth_date': '1975-12-10',
            'gender': 'male'
        }
        
        create_response = client.post('/api/v1/patients/', 
                                     json=patient_data, 
                                     headers=auth_headers)
        created_patient = create_response.get_json()
        patient_id = created_patient['id']
        
        response = client.get(f'/api/v1/patients/{patient_id}', 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Bob Johnson'
        assert data['gender'] == 'male'
    
    def test_update_patient(self, client, auth_headers):
        """Test updating a patient"""
        # Create a patient first
        patient_data = {
            'name': 'Alice Brown',
            'birth_date': '1985-07-22',
            'gender': 'female'
        }
        
        create_response = client.post('/api/v1/patients/', 
                                     json=patient_data, 
                                     headers=auth_headers)
        created_patient = create_response.get_json()
        patient_id = created_patient['id']
        
        # Update the patient
        update_data = {
            'name': 'Alice Updated',
            'notes': 'Updated patient'
        }
        
        response = client.put(f'/api/v1/patients/{patient_id}', 
                             json=update_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Alice Updated'
        assert data['notes'] == 'Updated patient'
    
    def test_delete_patient(self, client, auth_headers):
        """Test deleting a patient"""
        # Create a patient first
        patient_data = {
            'name': 'ToDelete Patient',
            'birth_date': '1990-01-01',
            'gender': 'male'
        }
        
        create_response = client.post('/api/v1/patients/', 
                                     json=patient_data, 
                                     headers=auth_headers)
        created_patient = create_response.get_json()
        patient_id = created_patient['id']
        
        # Verify patient exists
        get_response = client.get(f'/api/v1/patients/{patient_id}', 
                                 headers=auth_headers)
        assert get_response.status_code == 200
        
        # Delete the patient
        delete_response = client.delete(f'/api/v1/patients/{patient_id}', 
                                      headers=auth_headers)
        assert delete_response.status_code == 200
        
        # Verify patient is deleted
        get_response = client.get(f'/api/v1/patients/{patient_id}', 
                                 headers=auth_headers)
        assert get_response.status_code == 404


class TestFHIREndpoints:
    def test_patient_fhir_endpoint(self, client, auth_headers):
        """Test FHIR Patient endpoint"""
        # Create a patient first
        patient_data = {
            'name': 'FHIR Test Patient',
            'birth_date': '1980-01-01',
            'gender': 'male'
        }
        
        create_response = client.post('/api/v1/patients/', 
                                     json=patient_data, 
                                     headers=auth_headers)
        created_patient = create_response.get_json()
        fhir_id = created_patient['fhir_id']
        
        # Test GET FHIR Patient
        response = client.get(f'/fhir/Patient/{fhir_id}', 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['resourceType'] == 'Patient'
        assert data['id'] == fhir_id
        assert data['name'][0]['text'] == 'FHIR Test Patient'
    
    def test_observation_fhir_endpoint(self, client, auth_headers):
        """Test FHIR Observation endpoint"""
        # This would require creating a patient, biomarker, and observation first
        # For now, we'll test that the endpoint exists and requires auth
        response = client.get('/fhir/Observation/nonexistent-id')
        assert response.status_code == 401  # Unauthorized without auth
    
    def test_diagnostic_report_fhir_endpoint(self, client, auth_headers):
        """Test FHIR DiagnosticReport endpoint"""
        # Similar to observation, test that endpoint exists and requires auth
        response = client.get('/fhir/DiagnosticReport/nonexistent-id')
        assert response.status_code == 401  # Unauthorized without auth


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'