import pytest
import os
import tempfile
from datetime import datetime
from app import create_app, db
from app.models import Patient, TestReport, Observation, Biomarker, LOINCCode, UCUMUnit


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    
    # Create temporary database
    _, temp_db = tempfile.mkstemp(suffix='.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    with app.app_context():
        db.create_all()
        yield app
        
        # Clean up
        db.drop_all()
    os.unlink(temp_db)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestPatientModel:
    def test_create_patient(self, app):
        """Test creating a patient"""
        with app.app_context():
            patient = Patient(
                name="John Doe",
                birth_date=datetime(1980, 5, 15),
                gender="male",
                notes="Test patient"
            )
            
            db.session.add(patient)
            db.session.commit()
            
            assert patient.id is not None
            assert patient.name == "John Doe"
            assert patient.birth_date.year == 1980
            assert patient.gender == "male"
            assert patient.notes == "Test patient"
            assert patient.created_at is not None
            assert patient.updated_at is not None
    
    def test_patient_fhir_id_generation(self, app):
        """Test that FHIR ID is generated automatically"""
        with app.app_context():
            patient = Patient(name="Jane Doe")
            db.session.add(patient)
            db.session.commit()
            
            assert patient.fhir_id is not None
            assert len(patient.fhir_id) > 0


class TestBiomarkerModel:
    def test_create_biomarker(self, app):
        """Test creating a biomarker"""
        with app.app_context():
            biomarker = Biomarker(
                name="Glucose",
                default_ref_min=70,
                default_ref_max=100
            )
            
            db.session.add(biomarker)
            db.session.commit()
            
            assert biomarker.id is not None
            assert biomarker.name == "Glucose"
            assert biomarker.default_ref_min == 70
            assert biomarker.default_ref_max == 100


class TestLOINCCodeModel:
    def test_create_loinc_code(self, app):
        """Test creating a LOINC code"""
        with app.app_context():
            loinc_code = LOINCCode(
                code="2339-0",
                display="Glucose",
                component="Glucose",
                property="SCnc",
                time_aspect="Pt",
                system_analyzed="SerPl"
            )
            
            db.session.add(loinc_code)
            db.session.commit()
            
            assert loinc_code.id is not None
            assert loinc_code.code == "2339-0"
            assert loinc_code.display == "Glucose"


class TestUCUMUnitModel:
    def test_create_ucum_unit(self, app):
        """Test creating a UCUM unit"""
        with app.app_context():
            ucum_unit = UCUMUnit(
                code="mg/dL",
                display="milligram per deciliter"
            )
            
            db.session.add(ucum_unit)
            db.session.commit()
            
            assert ucum_unit.id is not None
            assert ucum_unit.code == "mg/dL"
            assert ucum_unit.display == "milligram per deciliter"


class TestTestReportModel:
    def test_create_report(self, app):
        """Test creating a test report"""
        with app.app_context():
            patient = Patient(name="John Doe")
            db.session.add(patient)
            db.session.commit()
            
            report = TestReport(
                patient_id=patient.id,
                effective_datetime=datetime(2023, 10, 15),
                status="final",
                category="laboratory",
                conclusion="Normal results"
            )
            
            db.session.add(report)
            db.session.commit()
            
            assert report.id is not None
            assert report.patient_id == patient.id
            assert report.effective_datetime.date() == datetime(2023, 10, 15).date()
            assert report.status == "final"
            assert report.category == "laboratory"
            assert report.conclusion == "Normal results"


class TestObservationModel:
    def test_create_observation(self, app):
        """Test creating an observation"""
        with app.app_context():
            # Create related objects
            patient = Patient(name="John Doe")
            db.session.add(patient)
            db.session.flush()
            
            biomarker = Biomarker(name="Glucose")
            db.session.add(biomarker)
            db.session.flush()
            
            report = TestReport(
                patient_id=patient.id,
                effective_datetime=datetime(2023, 10, 15),
                status="final"
            )
            db.session.add(report)
            db.session.flush()
            
            observation = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime=datetime(2023, 10, 15),
                value=95.5,
                unit="mg/dL",
                ref_min=70,
                ref_max=100,
                interpretation="N",
                notes="Within normal limits"
            )
            
            db.session.add(observation)
            db.session.commit()
            
            assert observation.id is not None
            assert observation.patient_id == patient.id
            assert observation.report_id == report.id
            assert observation.biomarker_id == biomarker.id
            assert observation.value == 95.5
            assert observation.unit == "mg/dL"
            assert observation.ref_min == 70
            assert observation.ref_max == 100
            assert observation.interpretation == "N"
            assert observation.notes == "Within normal limits"
    
    def test_observation_interpretation_logic(self, app):
        """Test that interpretation is set correctly based on value and reference range"""
        with app.app_context():
            # Create related objects
            patient = Patient(name="John Doe")
            db.session.add(patient)
            db.session.flush()
            
            biomarker = Biomarker(name="Glucose")
            db.session.add(biomarker)
            db.session.flush()
            
            report = TestReport(
                patient_id=patient.id,
                effective_datetime=datetime(2023, 10, 15),
                status="final"
            )
            db.session.add(report)
            db.session.flush()
            
            # Test low value
            obs_low = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime=datetime(2023, 10, 15),
                value=60,  # Below ref_min
                ref_min=70,
                ref_max=100
            )
            db.session.add(obs_low)
            
            # Test high value
            obs_high = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime=datetime(2023, 10, 15),
                value=110,  # Above ref_max
                ref_min=70,
                ref_max=100
            )
            db.session.add(obs_high)
            
            # Test normal value
            obs_normal = Observation(
                patient_id=patient.id,
                report_id=report.id,
                biomarker_id=biomarker.id,
                effective_datetime=datetime(2023, 10, 15),
                value=85,  # Within range
                ref_min=70,
                ref_max=100
            )
            db.session.add(obs_normal)
            
            db.session.commit()
            
            # Check interpretations
            assert obs_low.interpretation == "L"  # Low
            assert obs_high.interpretation == "H"  # High
            assert obs_normal.interpretation == "N"  # Normal