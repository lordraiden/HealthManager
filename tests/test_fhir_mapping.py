import pytest
from datetime import datetime, date
from app import create_app, db
from app.models import Patient, Biomarker, TestReport, Observation
from app.services.fhir_mapper import FHIRMapper


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


def test_patient_fhir_export(app):
    """Test FHIR Patient export structure"""
    with app.app_context():
        patient = Patient(
            name="John Doe",
            birth_date=date(1990, 5, 15),
            gender="male",
            notes="Test patient"
        )
        db.session.add(patient)
        db.session.commit()
        
        fhir_patient = FHIRMapper.patient_to_fhir(patient)
        
        assert fhir_patient['resourceType'] == 'Patient'
        assert 'id' in fhir_patient
        assert len(fhir_patient['name']) > 0
        assert fhir_patient['name'][0]['text'] == "John Doe"
        assert fhir_patient['gender'] == 'male'
        assert fhir_patient['birthDate'] == '1990-05-15'


def test_observation_fhir_export(app):
    """Test FHIR Observation export structure"""
    with app.app_context():
        patient = Patient(name="Jane Doe")
        db.session.add(patient)
        db.session.flush()  # This ensures the patient gets an ID
        
        biomarker = Biomarker(name="Glucose")
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
            value=95,
            unit="mg/dL",
            ref_min=70,
            ref_max=100,
            interpretation="N"
        )
        db.session.add(observation)
        db.session.commit()
        
        fhir_observation = FHIRMapper.observation_to_fhir(observation)
        
        assert fhir_observation['resourceType'] == 'Observation'
        assert 'id' in fhir_observation
        assert fhir_observation['status'] == 'final'
        assert fhir_observation['valueQuantity']['value'] == 95
        assert fhir_observation['valueQuantity']['unit'] == 'mg/dL'
        assert len(fhir_observation['referenceRange']) > 0


def test_report_fhir_export(app):
    """Test FHIR DiagnosticReport export structure"""
    with app.app_context():
        patient = Patient(name="John Smith")
        db.session.add(patient)
        db.session.flush()  # This ensures the patient gets an ID
        
        report = TestReport(
            patient_id=patient.id,
            effective_datetime=datetime.utcnow(),
            conclusion="Normal results"
        )
        db.session.add(report)
        db.session.commit()
        
        fhir_report = FHIRMapper.report_to_fhir(report)
        
        assert fhir_report['resourceType'] == 'DiagnosticReport'
        assert 'id' in fhir_report
        assert fhir_report['status'] == 'final'
        assert fhir_report['conclusion'] == 'Normal results'
        assert 'subject' in fhir_report
        assert fhir_report['subject']['reference'] == f'Patient/{patient.fhir_id}'


def test_patient_fhir_import(app):
    """Test FHIR Patient import"""
    with app.app_context():
        fhir_patient = {
            "resourceType": "Patient",
            "id": "test-patient-id",
            "name": [
                {
                    "use": "official",
                    "text": "Jane Smith"
                }
            ],
            "gender": "female",
            "birthDate": "1985-03-20",
            "note": [
                {
                    "text": "Test patient for import"
                }
            ]
        }
        
        patient = FHIRMapper.fhir_to_patient(fhir_patient)
        
        assert patient.name == "Jane Smith"
        assert patient.gender == "female"
        assert patient.birth_date == date(1985, 3, 20)
        assert patient.notes == "Test patient for import"
        assert patient.fhir_id == "test-patient-id"


def test_observation_fhir_import(app):
    """Test FHIR Observation import"""
    with app.app_context():
        fhir_obs = {
            "resourceType": "Observation",
            "id": "test-obs-id",
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "2339-0",
                        "display": "Glucose"
                    }
                ],
                "text": "Glucose"
            },
            "subject": {"reference": "Patient/1"},
            "effectiveDateTime": "2024-01-15T10:30:00Z",
            "valueQuantity": {
                "value": 95,
                "unit": "mg/dL",
                "system": "http://unitsofmeasure.org",
                "code": "mg/dL"
            },
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": "N",
                            "display": "Normal"
                        }
                    ]
                }
            ],
            "referenceRange": [
                {
                    "low": {
                        "value": 70,
                        "unit": "mg/dL",
                        "system": "http://unitsofmeasure.org",
                        "code": "mg/dL"
                    },
                    "high": {
                        "value": 100,
                        "unit": "mg/dL",
                        "system": "http://unitsofmeasure.org",
                        "code": "mg/dL"
                    }
                }
            ]
        }
        
        # We need a patient and report for the import
        patient = Patient(name="Test Patient")
        db.session.add(patient)
        db.session.commit()
        
        # Since we're testing the import functionality specifically, we'll use a placeholder biomarker_id
        # In a real scenario, we'd look up or create the biomarker based on the code
        observation = FHIRMapper.fhir_to_observation(fhir_obs, patient.id, 1)  # Using report_id=1 as placeholder
        
        assert observation.value == 95
        assert observation.unit == "mg/dL"
        assert observation.ref_min == 70
        assert observation.ref_max == 100
        assert observation.interpretation == "N"
        assert observation.fhir_id == "test-obs-id"


def test_create_bundle(app):
    """Test FHIR Bundle creation"""
    with app.app_context():
        patient = Patient(name="Bundle Test Patient")
        db.session.add(patient)
        db.session.commit()
        
        fhir_patient = FHIRMapper.patient_to_fhir(patient)
        
        resources = [fhir_patient]
        bundle = FHIRMapper.create_bundle(resources, "collection")
        
        assert bundle['resourceType'] == 'Bundle'
        assert bundle['type'] == 'collection'
        assert len(bundle['entry']) == 1
        assert bundle['entry'][0]['resource']['resourceType'] == 'Patient'
        assert bundle['entry'][0]['resource']['id'] == patient.fhir_id