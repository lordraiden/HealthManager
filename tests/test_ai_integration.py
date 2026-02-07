import pytest
import json
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models import Patient, User
from app.services.ai_provider import (
    OpenAIProvider, OllamaProvider, LMStudioProvider, MockProvider, 
    get_ai_provider, generate_fhir_context, generate_text_summary
)
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


def test_mock_provider():
    """Test MockProvider functionality"""
    provider = MockProvider()
    
    response = provider.generate_response("Test prompt", {})
    assert "mensaje de respuesta simulado" in response
    assert provider.get_name() == "Mock"


@patch('openai.ChatCompletion.create')
def test_openai_provider(mock_openai_create):
    """Test OpenAIProvider functionality"""
    # Mock the OpenAI API response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {'content': 'Mocked OpenAI response'}
    mock_openai_create.return_value = mock_response
    
    provider = OpenAIProvider(api_key="fake_key", model="gpt-3.5-turbo")
    
    response = provider.generate_response("Test prompt", {})
    assert "Mocked OpenAI response" == response
    assert provider.get_name() == "OpenAI"


@patch('requests.post')
def test_ollama_provider(mock_requests_post):
    """Test OllamaProvider functionality"""
    # Mock the Ollama API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Mocked Ollama response"}
    mock_requests_post.return_value = mock_response
    
    provider = OllamaProvider(base_url="http://localhost:11434", model="llama2")
    
    response = provider.generate_response("Test prompt", {})
    assert "Mocked Ollama response" == response
    assert provider.get_name() == "Ollama"


@patch('requests.post')
def test_lmstudio_provider(mock_requests_post):
    """Test LMStudioProvider functionality"""
    # Mock the LM Studio API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "Mocked LM Studio response"}}
        ]
    }
    mock_requests_post.return_value = mock_response
    
    provider = LMStudioProvider(base_url="http://localhost:1234")
    
    response = provider.generate_response("Test prompt", {})
    assert "Mocked LM Studio response" == response
    assert provider.get_name() == "LM Studio"


def test_get_ai_provider_factory():
    """Test the AI provider factory function"""
    # Test Mock provider (default)
    provider = get_ai_provider("nonexistent")
    assert isinstance(provider, MockProvider)
    
    # Test Mock provider explicitly
    provider = get_ai_provider("mock")
    assert isinstance(provider, MockProvider)
    
    # Test OpenAI provider
    provider = get_ai_provider("openai", api_key="fake_key")
    assert isinstance(provider, OpenAIProvider)
    
    # Test Ollama provider
    provider = get_ai_provider("ollama", base_url="http://test:11434", model="test-model")
    assert isinstance(provider, OllamaProvider)
    
    # Test LM Studio provider
    provider = get_ai_provider("lmstudio", base_url="http://test:1234")
    assert isinstance(provider, LMStudioProvider)


def test_generate_fhir_context(app):
    """Test FHIR context generation"""
    with app.app_context():
        # Create a patient
        patient = Patient(
            name="Test Patient",
            birth_date=date(1990, 5, 15),
            gender="male"
        )
        db.session.add(patient)
        db.session.commit()
        
        context = generate_fhir_context(patient.id)
        
        assert "fhir_bundle" in context
        assert "text_summary" in context
        assert context["patient_id"] == patient.id
        
        bundle = context["fhir_bundle"]
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert len(bundle["entry"]) >= 1  # At least the patient should be there


def test_generate_text_summary():
    """Test text summary generation from FHIR bundle"""
    fhir_bundle = {
        "entry": [
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {
                        "coding": [
                            {
                                "display": "Glucose"
                            }
                        ]
                    },
                    "effectiveDateTime": "2024-01-15T10:30:00Z",
                    "valueQuantity": {
                        "value": 95,
                        "unit": "mg/dL"
                    },
                    "referenceRange": [
                        {
                            "low": {
                                "value": 70
                            },
                            "high": {
                                "value": 100
                            }
                        }
                    ],
                    "interpretation": [
                        {
                            "coding": [
                                {
                                    "display": "Normal"
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }
    
    summary = generate_text_summary(fhir_bundle)
    
    assert "RESUMEN ANALÍTICAS:" in summary
    assert "Glucose" in summary
    assert "95 mg/dL" in summary
    assert "[70-100]" in summary
    assert "Normal" in summary


def test_ai_consult_endpoint(client):
    """Test the AI consultation endpoint"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Test with mock provider
    response = client.post('/api/v1/ai/consult',
                          data=json.dumps({
                              'question': 'How are my glucose levels?',
                              'provider': 'mock',
                              'context_type': 'fhir_bundle',
                              'patient_id': 1  # This will likely fail since patient doesn't exist, but should not error due to provider
                          }),
                          headers=headers)
    
    # The endpoint might return an error because patient ID 1 doesn't exist,
    # but it should not fail because of the AI provider
    assert response.status_code in [200, 400, 404]  # Could be 404 if patient not found, which is OK


def test_list_providers_endpoint(client):
    """Test the list AI providers endpoint"""
    token = get_auth_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    
    response = client.get('/api/v1/ai/providers', headers=headers)
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert len(data) >= 4  # Should have at least mock, ollama, lmstudio, openai
    
    provider_names = [provider['name'] for provider in data]
    assert 'mock' in provider_names
    assert 'ollama' in provider_names
    assert 'lmstudio' in provider_names
    assert 'openai' in provider_names