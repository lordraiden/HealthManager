import pytest
from datetime import datetime
from app import create_app, db
from app.models import Patient, TestReport, Observation, Biomarker, LOINCCode
from app.services.fhir_mapper import (
    get_patient_fhir, 
    get_observations_fhir, 
    get_reports_fhir, 
    generate_text_summary,
    generate_fhir_context
)


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
    
    with app.app_context():
        db.create_all()
        yield app
        
        # Clean up
        db.drop_all()
    os.unlink(temp_db)


class TestFHIRMapping:
    def test_patient_to_fhir_conversion(self, app):
        """Test converting Patient model to FHIR Patient resource"""
        with app.app_context():
            # Create a patient
            patient = Patient(
                name="John Doe",
                birth_date=datetime(1980, 5, 15),
                gender="male",
                notes="Test patient"
            )
            db.session.add(patient)
            db.session.commit()
            
            # Convert to FHIR
            fhir_patient = get_patient_fhir(patient.id)
            
            # Assert FHIR structure
            assert fhir_patient["resourceType"] == "Patient"
            assert fhir_patient["id"] is not None
            assert fhir_patient["name"][0]["text"] == "John Doe"
            assert fhir_patient["birthDate"] == "1980-05-15"
            assert fhir_patient["gender"] == "male"
            assert fhir_patient["note"][0]["text"] == "Test patient"
    
    def test_observation_to_fhir_conversion(self, app):
        """Test converting Observation model to FHIR Observation resource"""
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
                effective_datetime=datetime(2023, 10, 15, 10, 30),
                value=95.5,
                unit="mg/dL",
                ref_min=70,
                ref_max=100,
                interpretation="N",
                notes="Within normal limits"
            )
            db.session.add(observation)
            db.session.commit()
            
            # Get FHIR observations for the patient
            fhir_observations = get_observations_fhir(patient.id)
            
            # Should have one observation
            assert len(fhir_observations) == 1
            
            obs = fhir_observations[0]
            assert obs["resourceType"] == "Observation"
            assert obs["id"] is not None
            assert obs["status"] == "final"
            assert obs["valueQuantity"]["value"] == 95.5
            assert obs["valueQuantity"]["unit"] == "mg/dL"
            assert obs["interpretation"][0]["coding"][0]["display"] == "Normal"
            assert obs["note"][0]["text"] == "Within normal limits"
    
    def test_report_to_fhir_conversion(self, app):
        """Test converting TestReport model to FHIR DiagnosticReport resource"""
        with app.app_context():
            # Create related objects
            patient = Patient(name="John Doe")
            db.session.add(patient)
            db.session.flush()
            
            report = TestReport(
                patient_id=patient.id,
                effective_datetime=datetime(2023, 10, 15),
                status="final",
                category="laboratory",
                conclusion="Normal results"
            )
            db.session.add(report)
            db.session.commit()
            
            # Get FHIR reports for the patient
            fhir_reports = get_reports_fhir(patient.id)
            
            # Should have one report
            assert len(fhir_reports) == 1
            
            report_fhir = fhir_reports[0]
            assert report_fhir["resourceType"] == "DiagnosticReport"
            assert report_fhir["id"] is not None
            assert report_fhir["status"] == "final"
            assert report_fhir["category"][0]["coding"][0]["code"] == "LABORATORY"
            assert report_fhir["conclusion"] == "Normal results"
    
    def test_generate_text_summary(self, app):
        """Test generating text summary from FHIR bundle"""
        with app.app_context():
            # Create a simple FHIR bundle structure
            bundle = {
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Observation",
                            "code": {
                                "coding": [
                                    {
                                        "system": "http://loinc.org",
                                        "code": "2339-0",
                                        "display": "Glucose"
                                    }
                                ]
                            },
                            "effectiveDateTime": "2023-10-15T10:30:00",
                            "valueQuantity": {
                                "value": 95.5,
                                "unit": "mg/dL"
                            },
                            "referenceRange": [
                                {
                                    "low": {
                                        "value": 70,
                                        "unit": "mg/dL"
                                    },
                                    "high": {
                                        "value": 100,
                                        "unit": "mg/dL"
                                    }
                                }
                            ],
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
                            ]
                        }
                    }
                ]
            }
            
            summary = generate_text_summary(bundle)
            
            # Check that the summary contains expected elements
            assert "RESUMEN ANALÍTICAS:" in summary
            assert "Glucose" in summary
            assert "2023-10-15T10:30:00" in summary
            assert "95.5 mg/dL" in summary
            assert "[70-100]" in summary
            assert "Normal" in summary
    
    def test_generate_fhir_context(self, app):
        """Test generating complete FHIR context for a patient"""
        with app.app_context():
            # Create related objects
            patient = Patient(
                name="John Doe",
                birth_date=datetime(1980, 5, 15),
                gender="male"
            )
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
                effective_datetime=datetime(2023, 10, 15, 10, 30),
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
            
            # Check structure
            assert "fhir_bundle" in context
            assert "text_summary" in context
            assert "patient_id" in context
            assert context["patient_id"] == patient.id
            
            bundle = context["fhir_bundle"]
            assert bundle["resourceType"] == "Bundle"
            assert bundle["type"] == "collection"
            assert len(bundle["entry"]) >= 3  # Patient, Observation, Report
            
            # Check that text summary was generated
            assert len(context["text_summary"]) > 0
            assert "RESUMEN ANALÍTICAS:" in context["text_summary"]
    
    def test_observation_with_loinc_code(self, app):
        """Test observation conversion when LOINC code is available"""
        with app.app_context():
            # Create related objects including LOINC code
            patient = Patient(name="John Doe")
            db.session.add(patient)
            db.session.flush()
            
            loinc_code = LOINCCode(
                code="2339-0",
                display="Glucose"
            )
            db.session.add(loinc_code)
            db.session.flush()
            
            biomarker = Biomarker(
                name="Glucose",
                loinc_code_id=loinc_code.id
            )
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
                effective_datetime=datetime(2023, 10, 15, 10, 30),
                value=95.5,
                unit="mg/dL",
                ref_min=70,
                ref_max=100,
                interpretation="N"
            )
            db.session.add(observation)
            db.session.commit()
            
            # Get FHIR observations
            fhir_observations = get_observations_fhir(patient.id)
            
            # Check that LOINC code is included in the FHIR representation
            obs = fhir_observations[0]
            loinc_coding = None
            for coding in obs["code"]["coding"]:
                if coding["system"] == "http://loinc.org":
                    loinc_coding = coding
                    break
            
            assert loinc_coding is not None
            assert loinc_coding["code"] == "2339-0"
            assert loinc_coding["display"] == "Glucose"