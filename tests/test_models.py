import pytest
from datetime import datetime, date
from app import create_app, db
from app.models import Patient, Biomarker, TestReport, Observation, MedicalDocument, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_patient_model(app):
    """Test Patient model creation"""
    with app.app_context():
        patient = Patient(name="John Doe", birth_date=date(1990, 5, 15), gender="male")
        db.session.add(patient)
        db.session.commit()
        
        assert patient.id is not None
        assert patient.name == "John Doe"
        assert patient.birth_date == date(1990, 5, 15)
        assert patient.gender == "male"
        assert patient.fhir_id is not None


def test_biomarker_model(app):
    """Test Biomarker model creation"""
    with app.app_context():
        biomarker = Biomarker(name="Glucose", default_ref_min=70, default_ref_max=100)
        db.session.add(biomarker)
        db.session.commit()
        
        assert biomarker.id is not None
        assert biomarker.name == "Glucose"
        assert biomarker.default_ref_min == 70
        assert biomarker.default_ref_max == 100


def test_test_report_model(app):
    """Test TestReport model creation"""
    with app.app_context():
        patient = Patient(name="Jane Doe")
        db.session.add(patient)
        db.session.commit()
        
        report = TestReport(
            patient_id=patient.id,
            effective_datetime=datetime.utcnow()
        )
        db.session.add(report)
        db.session.commit()
        
        assert report.id is not None
        assert report.patient_id == patient.id
        assert report.fhir_id is not None


def test_observation_model(app):
    """Test Observation model creation"""
    with app.app_context():
        patient = Patient(name="Jane Doe")
        db.session.add(patient)
        db.session.flush()  # This ensures the patient gets an ID
        
        biomarker = Biomarker(name="Cholesterol")
        db.session.add(biomarker)
        
        report = TestReport(
            patient_id=patient.id,
            effective_datetime=datetime.utcnow()
        )
        db.session.add(report)
        db.session.flush()  # This ensures the report gets an ID
        
        db.session.commit()
        
        observation = Observation(
            patient_id=patient.id,
            report_id=report.id,
            biomarker_id=biomarker.id,
            effective_datetime=datetime.utcnow(),
            value=180,
            unit="mg/dL",
            ref_min=120,
            ref_max=200
        )
        db.session.add(observation)
        db.session.commit()
        
        assert observation.id is not None
        assert observation.patient_id == patient.id
        assert observation.value == 180
        assert observation.unit == "mg/dL"


def test_medical_document_model(app):
    """Test MedicalDocument model creation"""
    with app.app_context():
        patient = Patient(name="Jane Doe")
        db.session.add(patient)
        db.session.commit()
        
        document = MedicalDocument(
            patient_id=patient.id,
            filename="lab_results.pdf",
            filepath="/path/to/lab_results.pdf",
            file_type="pdf",
            file_size=1024
        )
        db.session.add(document)
        db.session.commit()
        
        assert document.id is not None
        assert document.patient_id == patient.id
        assert document.filename == "lab_results.pdf"
        assert document.file_type == "pdf"


def test_user_model(app):
    """Test User model creation"""
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        user = User(
            username="testuser",
            password_hash=generate_password_hash("password123"),
            email="test@example.com"
        )
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash is not None