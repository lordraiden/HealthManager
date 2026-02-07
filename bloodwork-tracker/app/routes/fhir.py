from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Patient, Observation, TestReport, LOINCCode, UCUMUnit, Biomarker
from app import db
from app.schemas import FHIRPatient, FHIRObservation, FHIRDiagnosticReport, FHIRBundle
from pydantic import ValidationError
import uuid
from datetime import datetime


bp = Blueprint('fhir', __name__)


def map_patient_to_fhir(patient):
    """Convert Patient model to FHIR Patient resource"""
    fhir_patient = {
        "resourceType": "Patient",
        "id": patient.fhir_id,
        "identifier": [
            {
                "use": "usual",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }
                    ]
                },
                "value": str(patient.id)
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "text": patient.name
            }
        ],
        "gender": patient.gender,
        "birthDate": patient.birth_date.isoformat() if patient.birth_date else None,
        "note": [
            {
                "text": patient.notes
            }
        ] if patient.notes else []
    }
    # Remove None values
    fhir_patient = {k: v for k, v in fhir_patient.items() if v is not None}
    return fhir_patient


def map_fhir_to_patient(fhir_data):
    """Convert FHIR Patient resource to Patient model"""
    patient_data = {
        "fhir_id": fhir_data.get("id") or str(uuid.uuid4()),
        "name": fhir_data["name"][0]["text"] if fhir_data.get("name") else "",
        "birth_date": datetime.fromisoformat(fhir_data["birthDate"]) if fhir_data.get("birthDate") else None,
        "gender": fhir_data.get("gender"),
        "notes": fhir_data["note"][0]["text"] if fhir_data.get("note") and len(fhir_data["note"]) > 0 else None
    }
    return patient_data


def map_observation_to_fhir(observation):
    """Convert Observation model to FHIR Observation resource"""
    fhir_obs = {
        "resourceType": "Observation",
        "id": observation.fhir_id,
        "status": observation.status,
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": observation.category,
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": []
        },
        "subject": {
            "reference": f"Patient/{observation.patient.fhir_id}"
        },
        "effectiveDateTime": observation.effective_datetime.isoformat() if observation.effective_datetime else None,
        "issued": observation.issued.isoformat() if observation.issued else None,
        "valueQuantity": {
            "value": observation.value,
            "unit": observation.unit,
            "system": "http://unitsofmeasure.org",
            "code": observation.unit
        } if observation.value is not None else None,
        "referenceRange": [
            {
                "low": {
                    "value": observation.ref_min,
                    "unit": observation.unit
                } if observation.ref_min is not None else None,
                "high": {
                    "value": observation.ref_max,
                    "unit": observation.unit
                } if observation.ref_max is not None else None
            }
        ] if observation.ref_min is not None or observation.ref_max is not None else [],
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": observation.interpretation,
                        "display": get_interpretation_display(observation.interpretation)
                    }
                ]
            }
        ] if observation.interpretation else [],
        "performer": [
            {
                "reference": f"Organization/{observation.performer}"
            }
        ] if observation.performer else [],
        "specimen": {
            "reference": f"Specimen/{observation.specimen}"
        } if observation.specimen else None,
        "method": {
            "coding": [
                {
                    "system": "http://example.org/methods",
                    "code": observation.method,
                    "display": observation.method
                }
            ]
        } if observation.method else None,
        "note": [
            {
                "text": observation.notes
            }
        ] if observation.notes else []
    }
    
    # Add LOINC code if available
    if observation.biomarker and observation.biomarker.loinc:
        fhir_obs["code"]["coding"].append({
            "system": "http://loinc.org",
            "code": observation.biomarker.loinc.code,
            "display": observation.biomarker.loinc.display
        })
    else:
        # Add a generic code if no LOINC is available
        fhir_obs["code"]["coding"].append({
            "system": "http://example.org/local-codes",
            "code": f"local-{observation.biomarker_id}",
            "display": observation.biomarker.name if observation.biomarker else "Unknown"
        })
    
    # Remove None values
    fhir_obs = {k: v for k, v in fhir_obs.items() if v is not None and 
                (not isinstance(v, list) or any(item is not None for item in v))}
    for key in list(fhir_obs.keys()):
        if isinstance(fhir_obs[key], dict) and all(v is None for v in fhir_obs[key].values()):
            del fhir_obs[key]
        elif isinstance(fhir_obs[key], list) and all(
            isinstance(item, dict) and all(v is None for v in item.values()) if isinstance(item, dict) else item is None
            for item in fhir_obs[key]
        ):
            del fhir_obs[key]
    
    return fhir_obs


def get_interpretation_display(interp_code):
    """Get display text for interpretation codes"""
    interpretations = {
        'L': 'Low',
        'H': 'High',
        'N': 'Normal',
        'A': 'Abnormal',
        'AA': 'Critical abnormal'
    }
    return interpretations.get(interp_code, interp_code)


def map_fhir_to_observation(fhir_data):
    """Convert FHIR Observation resource to Observation model"""
    # Find or create biomarker based on LOINC code
    loinc_code = None
    if 'code' in fhir_data and 'coding' in fhir_data['code']:
        for coding in fhir_data['code']['coding']:
            if coding.get('system') == 'http://loinc.org':
                loinc_code = coding['code']
                break
    
    biomarker = None
    if loinc_code:
        loinc_obj = LOINCCode.query.filter_by(code=loinc_code).first()
        if loinc_obj:
            biomarker = Biomarker.query.filter_by(loinc_code_id=loinc_obj.id).first()
    
    # If no existing biomarker, create a basic one
    if not biomarker:
        biomarker_name = fhir_data['code']['coding'][0]['display'] if fhir_data['code']['coding'] else 'Unknown'
        biomarker = Biomarker(name=biomarker_name)
        db.session.add(biomarker)
        db.session.flush()  # To get the ID
    
    observation_data = {
        "fhir_id": fhir_data.get("id") or str(uuid.uuid4()),
        "status": fhir_data.get("status", "final"),
        "category": fhir_data["category"][0]["coding"][0]["code"] if fhir_data.get("category") else "laboratory",
        "biomarker_id": biomarker.id,
        "effective_datetime": datetime.fromisoformat(fhir_data["effectiveDateTime"]) if fhir_data.get("effectiveDateTime") else datetime.utcnow(),
        "value": fhir_data["valueQuantity"]["value"] if fhir_data.get("valueQuantity") else None,
        "unit": fhir_data["valueQuantity"]["unit"] if fhir_data.get("valueQuantity") else None,
        "ref_min": fhir_data["referenceRange"][0]["low"]["value"] if fhir_data.get("referenceRange") and fhir_data["referenceRange"][0].get("low") else None,
        "ref_max": fhir_data["referenceRange"][0]["high"]["value"] if fhir_data.get("referenceRange") and fhir_data["referenceRange"][0].get("high") else None,
        "interpretation": fhir_data["interpretation"][0]["coding"][0]["code"] if fhir_data.get("interpretation") else None,
        "notes": fhir_data["note"][0]["text"] if fhir_data.get("note") and len(fhir_data["note"]) > 0 else None,
        "performer": fhir_data["performer"][0]["reference"].replace("Organization/", "") if fhir_data.get("performer") else None,
        "specimen": fhir_data["specimen"]["reference"].replace("Specimen/", "") if fhir_data.get("specimen") else None,
        "method": fhir_data["method"]["coding"][0]["code"] if fhir_data.get("method") else None
    }
    
    # Extract patient ID from subject reference
    subject_ref = fhir_data.get("subject", {}).get("reference", "")
    if subject_ref.startswith("Patient/"):
        patient_fhir_id = subject_ref.replace("Patient/", "")
        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
        if patient:
            observation_data["patient_id"] = patient.id
    
    # Extract report ID if mentioned in related resources
    # For now, we'll need to associate it separately or create a new report
    
    return observation_data


def map_report_to_fhir(report):
    """Convert TestReport model to FHIR DiagnosticReport resource"""
    fhir_report = {
        "resourceType": "DiagnosticReport",
        "id": report.fhir_id,
        "status": report.status,
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": report.category.upper(),
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "24323-8",
                    "display": "Laboratory studies (set)"
                }
            ]
        },
        "subject": {
            "reference": f"Patient/{report.patient.fhir_id}"
        },
        "effectiveDateTime": report.effective_datetime.isoformat() if report.effective_datetime else None,
        "issued": report.issued.isoformat() if report.issued else None,
        "performer": [
            {
                "reference": "Organization/lab-organization"
            }
        ],
        "result": [
            {
                "reference": f"Observation/{obs.fhir_id}"
            } for obs in report.observations
        ] if report.observations else [],
        "conclusion": report.conclusion,
        "conclusionCode": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "normal",
                        "display": "Normal"
                    }
                ]
            }
        ] if report.conclusion else []
    }
    
    # Remove None values
    fhir_report = {k: v for k, v in fhir_report.items() if v is not None}
    return fhir_report


@bp.route('/Patient', methods=['GET'])
@jwt_required()
def search_patients():
    """Search patients with FHIR-style parameters"""
    try:
        # Simple implementation - could be expanded with more FHIR search parameters
        patients = Patient.query.all()
        fhir_patients = [map_patient_to_fhir(p) for p in patients]
        
        # Wrap in a bundle
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(fhir_patients),
            "entry": [{"resource": p} for p in fhir_patients]
        }
        
        return jsonify(bundle), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/Patient/<fhir_id>', methods=['GET'])
@jwt_required()
def get_patient_fhir(fhir_id):
    """Get a specific patient by FHIR ID"""
    try:
        patient = Patient.query.filter_by(fhir_id=fhir_id).first_or_404()
        fhir_patient = map_patient_to_fhir(patient)
        return jsonify(fhir_patient), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/Patient/<fhir_id>', methods=['PUT'])
@jwt_required()
def update_patient_fhir(fhir_id):
    """Update a patient from FHIR resource"""
    try:
        fhir_data = request.json
        
        # Validate FHIR data
        FHIRPatient(**fhir_data)
        
        # Find existing patient
        patient = Patient.query.filter_by(fhir_id=fhir_id).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Update patient from FHIR data
        patient_data = map_fhir_to_patient(fhir_data)
        
        for field, value in patient_data.items():
            if hasattr(patient, field) and field != 'fhir_id':  # Don't update fhir_id
                setattr(patient, field, value)
        
        db.session.commit()
        
        # Return updated patient
        updated_fhir = map_patient_to_fhir(patient)
        return jsonify(updated_fhir), 200
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/Patient/<fhir_id>', methods=['DELETE'])
@jwt_required()
def delete_patient_fhir(fhir_id):
    """Delete a patient by FHIR ID"""
    try:
        patient = Patient.query.filter_by(fhir_id=fhir_id).first_or_404()
        db.session.delete(patient)
        db.session.commit()
        
        return '', 204  # No content for successful deletion
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/Patient', methods=['POST'])
@jwt_required()
def create_patient_fhir():
    """Create a patient from FHIR resource"""
    try:
        fhir_data = request.json
        
        # Validate FHIR data
        FHIRPatient(**fhir_data)
        
        # Check if we've reached the max patient limit (4)
        patient_count = Patient.query.count()
        if patient_count >= 4:
            return jsonify({'error': 'Maximum number of patients (4) reached'}), 400
        
        # Create patient from FHIR data
        patient_data = map_fhir_to_patient(fhir_data)
        patient = Patient(**patient_data)
        
        db.session.add(patient)
        db.session.commit()
        
        # Return created patient
        fhir_patient = map_patient_to_fhir(patient)
        return jsonify(fhir_patient), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/Observation', methods=['GET'])
@jwt_required()
def search_observations():
    """Search observations with FHIR-style parameters"""
    try:
        patient_fhir_id = request.args.get('patient')
        code = request.args.get('code')  # LOINC code
        date_from = request.args.get('date=ge')  # Format: YYYY-MM-DD
        date_to = request.args.get('date=le')   # Format: YYYY-MM-DD
        
        query = Observation.query
        
        if patient_fhir_id:
            # Join with Patient table to filter by FHIR ID
            query = query.join(Patient).filter(Patient.fhir_id == patient_fhir_id)
        
        if code:
            # Join with Biomarker and LOINCCode to filter by LOINC code
            query = query.join(Biomarker).join(LOINCCode).filter(LOINCCode.code == code)
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Observation.effective_datetime >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Observation.effective_datetime <= date_to_obj)
        
        observations = query.all()
        fhir_observations = [map_observation_to_fhir(obs) for obs in observations]
        
        # Wrap in a bundle
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(fhir_observations),
            "entry": [{"resource": obs} for obs in fhir_observations]
        }
        
        return jsonify(bundle), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/Observation/<fhir_id>', methods=['GET'])
@jwt_required()
def get_observation_fhir(fhir_id):
    """Get a specific observation by FHIR ID"""
    try:
        observation = Observation.query.filter_by(fhir_id=fhir_id).first_or_404()
        fhir_obs = map_observation_to_fhir(observation)
        return jsonify(fhir_obs), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/Observation', methods=['POST'])
@jwt_required()
def create_observation_fhir():
    """Create an observation from FHIR resource"""
    try:
        fhir_data = request.json
        
        # Validate FHIR data
        FHIRObservation(**fhir_data)
        
        # Create observation from FHIR data
        observation_data = map_fhir_to_observation(fhir_data)
        
        # Need to get report_id somehow - for now, create a default report if needed
        # In practice, you'd likely pass this or have other logic
        if 'report_id' not in observation_data or not observation_data['report_id']:
            # Create a default report for this observation
            from app.models import TestReport
            patient = Patient.query.get(observation_data['patient_id'])
            if patient:
                report = TestReport(
                    patient_id=patient.id,
                    effective_datetime=observation_data['effective_datetime'],
                    status="final",
                    category="laboratory"
                )
                db.session.add(report)
                db.session.flush()  # Get the ID
                observation_data['report_id'] = report.id
        
        observation = Observation(**observation_data)
        
        db.session.add(observation)
        db.session.commit()
        
        # Return created observation
        fhir_obs = map_observation_to_fhir(observation)
        return jsonify(fhir_obs), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/Observation/<fhir_id>', methods=['PUT'])
@jwt_required()
def update_observation_fhir(fhir_id):
    """Update an observation from FHIR resource"""
    try:
        fhir_data = request.json
        
        # Validate FHIR data
        FHIRObservation(**fhir_data)
        
        # Find existing observation
        observation = Observation.query.filter_by(fhir_id=fhir_id).first()
        if not observation:
            return jsonify({'error': 'Observation not found'}), 404
        
        # Update observation from FHIR data
        observation_data = map_fhir_to_observation(fhir_data)
        
        for field, value in observation_data.items():
            if hasattr(observation, field) and field != 'fhir_id':  # Don't update fhir_id
                setattr(observation, field, value)
        
        db.session.commit()
        
        # Return updated observation
        updated_fhir = map_observation_to_fhir(observation)
        return jsonify(updated_fhir), 200
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/Observation/<fhir_id>', methods=['DELETE'])
@jwt_required()
def delete_observation_fhir(fhir_id):
    """Delete an observation by FHIR ID"""
    try:
        observation = Observation.query.filter_by(fhir_id=fhir_id).first_or_404()
        db.session.delete(observation)
        db.session.commit()
        
        return '', 204  # No content for successful deletion
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/DiagnosticReport', methods=['GET'])
@jwt_required()
def search_reports():
    """Search diagnostic reports with FHIR-style parameters"""
    try:
        patient_fhir_id = request.args.get('patient')
        category = request.args.get('category')
        
        query = TestReport.query
        
        if patient_fhir_id:
            # Join with Patient table to filter by FHIR ID
            query = query.join(Patient).filter(Patient.fhir_id == patient_fhir_id)
        
        if category:
            query = query.filter(TestReport.category.ilike(f'%{category}%'))
        
        reports = query.all()
        fhir_reports = [map_report_to_fhir(rep) for rep in reports]
        
        # Wrap in a bundle
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(fhir_reports),
            "entry": [{"resource": rep} for rep in fhir_reports]
        }
        
        return jsonify(bundle), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/DiagnosticReport/<fhir_id>', methods=['GET'])
@jwt_required()
def get_report_fhir(fhir_id):
    """Get a specific diagnostic report by FHIR ID"""
    try:
        report = TestReport.query.filter_by(fhir_id=fhir_id).first_or_404()
        fhir_report = map_report_to_fhir(report)
        return jsonify(fhir_report), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/DiagnosticReport', methods=['POST'])
@jwt_required()
def create_report_fhir():
    """Create a diagnostic report from FHIR resource"""
    try:
        fhir_data = request.json
        
        # Validate FHIR data
        FHIRDiagnosticReport(**fhir_data)
        
        # Extract patient ID from subject reference
        subject_ref = fhir_data.get("subject", {}).get("reference", "")
        patient_id = None
        if subject_ref.startswith("Patient/"):
            patient_fhir_id = subject_ref.replace("Patient/", "")
            patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
            if patient:
                patient_id = patient.id
        
        if not patient_id:
            return jsonify({'error': 'Patient reference is required and must be valid'}), 400
        
        report_data = {
            "fhir_id": fhir_data.get("id") or str(uuid.uuid4()),
            "patient_id": patient_id,
            "status": fhir_data.get("status", "final"),
            "category": fhir_data["category"][0]["coding"][0]["code"] if fhir_data.get("category") else "laboratory",
            "effective_datetime": datetime.fromisoformat(fhir_data["effectiveDateTime"]) if fhir_data.get("effectiveDateTime") else datetime.utcnow(),
            "conclusion": fhir_data.get("conclusion"),
            "conclusion_code": fhir_data["conclusionCode"][0]["coding"][0]["code"] if fhir_data.get("conclusionCode") else None
        }
        
        report = TestReport(**report_data)
        
        db.session.add(report)
        db.session.commit()
        
        # Return created report
        fhir_report = map_report_to_fhir(report)
        return jsonify(fhir_report), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/DiagnosticReport/<fhir_id>', methods=['PUT'])
@jwt_required()
def update_report_fhir(fhir_id):
    """Update a diagnostic report from FHIR resource"""
    try:
        fhir_data = request.json
        
        # Validate FHIR data
        FHIRDiagnosticReport(**fhir_data)
        
        # Find existing report
        report = TestReport.query.filter_by(fhir_id=fhir_id).first()
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Extract patient ID from subject reference
        subject_ref = fhir_data.get("subject", {}).get("reference", "")
        if subject_ref.startswith("Patient/"):
            patient_fhir_id = subject_ref.replace("Patient/", "")
            patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
            if patient:
                report.patient_id = patient.id
        
        # Update other fields
        report.status = fhir_data.get("status", report.status)
        report.category = fhir_data["category"][0]["coding"][0]["code"] if fhir_data.get("category") else report.category
        report.effective_datetime = datetime.fromisoformat(fhir_data["effectiveDateTime"]) if fhir_data.get("effectiveDateTime") else report.effective_datetime
        report.conclusion = fhir_data.get("conclusion")
        report.conclusion_code = fhir_data["conclusionCode"][0]["coding"][0]["code"] if fhir_data.get("conclusionCode") else None
        
        db.session.commit()
        
        # Return updated report
        updated_fhir = map_report_to_fhir(report)
        return jsonify(updated_fhir), 200
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/DiagnosticReport/<fhir_id>', methods=['DELETE'])
@jwt_required()
def delete_report_fhir(fhir_id):
    """Delete a diagnostic report by FHIR ID"""
    try:
        report = TestReport.query.filter_by(fhir_id=fhir_id).first_or_404()
        db.session.delete(report)
        db.session.commit()
        
        return '', 204  # No content for successful deletion
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/Bundle', methods=['GET'])
@jwt_required()
def get_bundle():
    """Get a bundle of patient data (FHIR Bundle)"""
    try:
        patient_fhir_id = request.args.get('patient')
        bundle_type = request.args.get('type', 'collection')
        
        if not patient_fhir_id:
            return jsonify({'error': 'Patient ID is required'}), 400
        
        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first_or_404()
        
        # Create bundle with patient, observations, and reports
        bundle_entries = []
        
        # Add patient
        patient_fhir = map_patient_to_fhir(patient)
        bundle_entries.append({
            "fullUrl": f"http://localhost:5000/fhir/Patient/{patient.fhir_id}",
            "resource": patient_fhir
        })
        
        # Add reports
        for report in patient.reports:
            report_fhir = map_report_to_fhir(report)
            bundle_entries.append({
                "fullUrl": f"http://localhost:5000/fhir/DiagnosticReport/{report.fhir_id}",
                "resource": report_fhir
            })
        
        # Add observations
        for observation in patient.observations:
            obs_fhir = map_observation_to_fhir(observation)
            bundle_entries.append({
                "fullUrl": f"http://localhost:5000/fhir/Observation/{observation.fhir_id}",
                "resource": obs_fhir
            })
        
        bundle = {
            "resourceType": "Bundle",
            "type": bundle_type,
            "entry": bundle_entries
        }
        
        return jsonify(bundle), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/Bundle', methods=['POST'])
@jwt_required()
def post_bundle():
    """Post a bundle of FHIR resources (for import)"""
    try:
        fhir_bundle = request.json
        
        if fhir_bundle.get('resourceType') != 'Bundle':
            return jsonify({'error': 'Resource must be a Bundle'}), 400
        
        entries = fhir_bundle.get('entry', [])
        imported_resources = []
        
        for entry in entries:
            resource = entry.get('resource', {})
            resource_type = resource.get('resourceType')
            
            if resource_type == 'Patient':
                # Create or update patient
                patient = Patient.query.filter_by(fhir_id=resource.get('id')).first()
                if patient:
                    # Update existing patient
                    patient_data = map_fhir_to_patient(resource)
                    for field, value in patient_data.items():
                        if hasattr(patient, field) and field != 'fhir_id':
                            setattr(patient, field, value)
                else:
                    # Create new patient
                    patient_data = map_fhir_to_patient(resource)
                    patient = Patient(**patient_data)
                    db.session.add(patient)
                
                db.session.flush()  # Get the ID if newly created
                imported_resources.append(f"Patient/{patient.fhir_id}")
            
            elif resource_type == 'Observation':
                # Create or update observation
                observation = Observation.query.filter_by(fhir_id=resource.get('id')).first()
                if observation:
                    # Update existing observation
                    observation_data = map_fhir_to_observation(resource)
                    for field, value in observation_data.items():
                        if hasattr(observation, field) and field != 'fhir_id':
                            setattr(observation, field, value)
                else:
                    # Create new observation
                    observation_data = map_fhir_to_observation(resource)
                    
                    # Make sure patient exists and get patient_id
                    subject_ref = resource.get("subject", {}).get("reference", "")
                    if subject_ref.startswith("Patient/"):
                        patient_fhir_id = subject_ref.replace("Patient/", "")
                        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
                        if patient:
                            observation_data["patient_id"] = patient.id
                    
                    # If no report_id was determined, create a default report
                    if 'report_id' not in observation_data or not observation_data['report_id']:
                        # Create a default report for this observation
                        patient = Patient.query.get(observation_data['patient_id'])
                        if patient:
                            report = TestReport(
                                patient_id=patient.id,
                                effective_datetime=observation_data['effective_datetime'],
                                status="final",
                                category="laboratory"
                            )
                            db.session.add(report)
                            db.session.flush()  # Get the ID
                            observation_data['report_id'] = report.id
                    
                    observation = Observation(**observation_data)
                    db.session.add(observation)
                
                db.session.flush()  # Get the ID if newly created
                imported_resources.append(f"Observation/{observation.fhir_id}")
            
            elif resource_type == 'DiagnosticReport':
                # Create or update report
                report = TestReport.query.filter_by(fhir_id=resource.get('id')).first()
                if report:
                    # Update existing report
                    subject_ref = resource.get("subject", {}).get("reference", "")
                    if subject_ref.startswith("Patient/"):
                        patient_fhir_id = subject_ref.replace("Patient/", "")
                        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
                        if patient:
                            report.patient_id = patient.id
                    
                    report.status = resource.get("status", report.status)
                    report.category = resource["category"][0]["coding"][0]["code"] if resource.get("category") else report.category
                    report.effective_datetime = datetime.fromisoformat(resource["effectiveDateTime"]) if resource.get("effectiveDateTime") else report.effective_datetime
                    report.conclusion = resource.get("conclusion")
                    report.conclusion_code = resource["conclusionCode"][0]["coding"][0]["code"] if resource.get("conclusionCode") else None
                else:
                    # Create new report
                    subject_ref = resource.get("subject", {}).get("reference", "")
                    patient_id = None
                    if subject_ref.startswith("Patient/"):
                        patient_fhir_id = subject_ref.replace("Patient/", "")
                        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
                        if patient:
                            patient_id = patient.id
                    
                    if not patient_id:
                        continue  # Skip if no valid patient reference
                    
                    report_data = {
                        "fhir_id": resource.get("id") or str(uuid.uuid4()),
                        "patient_id": patient_id,
                        "status": resource.get("status", "final"),
                        "category": resource["category"][0]["coding"][0]["code"] if resource.get("category") else "laboratory",
                        "effective_datetime": datetime.fromisoformat(resource["effectiveDateTime"]) if resource.get("effectiveDateTime") else datetime.utcnow(),
                        "conclusion": resource.get("conclusion"),
                        "conclusion_code": resource["conclusionCode"][0]["coding"][0]["code"] if resource.get("conclusionCode") else None
                    }
                    
                    report = TestReport(**report_data)
                    db.session.add(report)
                
                db.session.flush()  # Get the ID if newly created
                imported_resources.append(f"DiagnosticReport/{report.fhir_id}")
        
        db.session.commit()
        
        return jsonify({
            "message": f"Successfully imported {len(imported_resources)} resources",
            "resources": imported_resources
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500