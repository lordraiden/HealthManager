import pytest
from unittest.mock import Mock, patch
from app import create_app, db
from app.models import Patient, TestReport, Observation, Biomarker
from app.services.ai_provider import AIProviderFactory, OpenAIProvider, OllamaProvider, LMStudioProvider, MockProvider
from app.services.fhir_mapper import generate_fhir_context


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
        yield app
        
        # Clean up
        db.drop_all()
    os.unlink(temp_db)


class TestAIProviderFactory:
    def test_get_mock_provider(self):
        """Test retrieving the mock provider"""
        provider = AIProviderFactory.get_provider('mock')
        assert provider is not None
        assert isinstance(provider, MockProvider)
        assert provider.get_name() == "Mock"
    
    def test_get_available_providers(self):
        """Test listing available providers"""
        providers = AIProviderFactory.get_available_providers()
        assert 'mock' in providers
        assert 'openai' in providers
        assert 'ollama' in providers
        assert 'lmstudio' in providers
        assert len(providers) == 4
    
    def test_case_insensitive_lookup(self):
        """Test that provider lookup is case insensitive"""
        provider_upper = AIProviderFactory.get_provider('MOCK')
        provider_lower = AIProviderFactory.get_provider('mock')
        assert type(provider_upper) == type(provider_lower)
        assert provider_upper.get_name() == provider_lower.get_name()
    
    def test_invalid_provider(self):
        """Test that invalid provider returns None"""
        provider = AIProviderFactory.get_provider('invalid_provider')
        assert provider is None


class TestMockProvider:
    def test_mock_provider_response(self):
        """Test that mock provider returns expected response"""
        provider = MockProvider()
        response = provider.generate_response("test prompt", {})
        assert response == "This is a mock response for testing purposes. In a real implementation, this would connect to an AI service."
    
    def test_mock_provider_name(self):
        """Test that mock provider returns correct name"""
        provider = MockProvider()
        assert provider.get_name() == "Mock"


class TestOpenAIProvider:
    @patch('openai.ChatCompletion.create')
    def test_openai_provider_response(self, mock_create):
        """Test OpenAI provider response"""
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Mocked OpenAI response"
        
        mock_create.return_value = mock_response
        
        provider = OpenAIProvider(api_key='fake_key')
        response = provider.generate_response("test prompt", {})
        
        assert response == "Mocked OpenAI response"
        assert provider.get_name() == "OpenAI"
        mock_create.assert_called_once()


class TestOllamaProvider:
    @patch('requests.post')
    def test_ollama_provider_response(self, mock_post):
        """Test Ollama provider response"""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Mocked Ollama response"}
        
        mock_post.return_value = mock_response
        
        provider = OllamaProvider(base_url='http://localhost:11434')
        response = provider.generate_response("test prompt", {})
        
        assert response == "Mocked Ollama response"
        assert provider.get_name() == "Ollama"
        mock_post.assert_called_once()


class TestLMStudioProvider:
    @patch('requests.post')
    def test_lmstudio_provider_response(self, mock_post):
        """Test LM Studio provider response"""
        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Mocked LM Studio response"
                    }
                }
            ]
        }
        
        mock_post.return_value = mock_response
        
        provider = LMStudioProvider(base_url='http://localhost:1234')
        response = provider.generate_response("test prompt", {})
        
        assert response == "Mocked LM Studio response"
        assert provider.get_name() == "LM Studio"
        mock_post.assert_called_once()


class TestFHIRContextGeneration:
    def test_generate_fhir_context(self, app):
        """Test generating FHIR context for AI consumption"""
        with app.app_context():
            # Create test patient
            patient = Patient(
                name="John Doe",
                birth_date="1980-05-15",
                gender="male"
            )
            db.session.add(patient)
            db.session.flush()
            
            # Create biomarker
            biomarker = Biomarker(
                name="Glucose",
                default_ref_min=70,
                default_ref_max=100
            )
            db.session.add(biomarker)
            db.session.flush()
            
            # Create report
            report = TestReport(
                patient_id=patient.id,
                effective_datetime="2023-10-15T10:30:00",
                status="final"
            )
            db.session.add(report)
            db.session.flush()
            
            # Create observation
            observation = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime="2023-10-15T10:30:00",
                value=95.5,
                unit="mg/dL",
                ref_min=70,
                ref_max=100,
                interpretation="N"
            )
            db.session.add(observation)
            db.session.commit()
            
            # Generate FHIR context
            context = generate_fhir_context(patient.id)
            
            # Verify context structure
            assert "fhir_bundle" in context
            assert "text_summary" in context
            assert "patient_id" in context
            assert context["patient_id"] == patient.id
            
            # Verify bundle structure
            bundle = context["fhir_bundle"]
            assert bundle["resourceType"] == "Bundle"
            assert bundle["type"] == "collection"
            assert len(bundle["entry"]) >= 3  # Patient, Observation, Report
            
            # Verify text summary contains patient info
            summary = context["text_summary"]
            assert "RESUMEN ANALÍTICAS:" in summary
            assert "John Doe" in summary or "Glucose" in summary  # Either patient name or biomarker should appear
    
    def test_generate_text_summary_structure(self, app):
        """Test the structure of generated text summary"""
        with app.app_context():
            # Create test data
            patient = Patient(name="Jane Smith", birth_date="1990-01-01", gender="female")
            db.session.add(patient)
            db.session.flush()
            
            biomarker = Biomarker(name="Cholesterol", default_ref_min=120, default_ref_max=200)
            db.session.add(biomarker)
            db.session.flush()
            
            report = TestReport(
                patient_id=patient.id,
                effective_datetime="2023-11-20T09:15:00",
                status="final"
            )
            db.session.add(report)
            db.session.flush()
            
            observation = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime="2023-11-20T09:15:00",
                value=180,
                unit="mg/dL",
                ref_min=120,
                ref_max=200,
                interpretation="N"
            )
            db.session.add(observation)
            db.session.commit()
            
            # Generate context and check summary
            context = generate_fhir_context(patient.id)
            summary = context["text_summary"]
            
            # Summary should contain key information
            assert "Cholesterol" in summary
            assert "180" in summary
            assert "mg/dL" in summary
            assert "[120-200]" in summary
            assert "Normal" in summary


class TestAIIntegrationWithFHIR:
    def test_ai_consult_with_fhir_context(self, app):
        """Test AI consultation with FHIR context"""
        with app.app_context():
            # Create test patient with some data
            patient = Patient(
                name="AI Test Patient",
                birth_date="1975-06-15",
                gender="male"
            )
            db.session.add(patient)
            db.session.flush()
            
            biomarker = Biomarker(name="Creatinine", default_ref_min=0.7, default_ref_max=1.3)
            db.session.add(biomarker)
            db.session.flush()
            
            report = TestReport(
                patient_id=patient.id,
                effective_datetime="2023-12-01T14:30:00",
                status="final"
            )
            db.session.add(report)
            db.session.flush()
            
            observation = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime="2023-12-01T14:30:00",
                value=1.1,
                unit="mg/dL",
                ref_min=0.7,
                ref_max=1.3,
                interpretation="N"
            )
            db.session.add(observation)
            db.session.commit()
            
            # Test with mock provider
            provider = MockProvider()
            context = generate_fhir_context(patient.id)
            
            # Create a prompt that includes patient data
            prompt = f"""
            Based on the following patient data:
            {context.get('text_summary', '')}
            
            Provide general feedback about the results.
            """
            
            response = provider.generate_response(prompt, context)
            
            # The mock provider should return its standard response regardless of input
            assert "This is a mock response for testing purposes" in response