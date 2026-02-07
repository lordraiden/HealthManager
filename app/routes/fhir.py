from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Patient, Observation, TestReport
from app.services.fhir_mapper import FHIRMapper
from app import db
from datetime import datetime

bp = Blueprint('fhir', __name__, url_prefix='/fhir')


@bp.route('/Patient', methods=['GET'])
@jwt_required()
def search_patients():
    # Basic search parameters
    name = request.args.get('_name')
    identifier = request.args.get('identifier')
    
    query = Patient.query
    
    if name:
        query = query.filter(Patient.name.contains(name))
    
    if identifier:
        query = query.filter(Patient.id == identifier)
    
    # Apply pagination
    page = request.args.get('page', 1, type=int)
    count = min(request.args.get('_count', 20, type=int), 100)  # FHIR-style pagination
    
    patients = query.paginate(page=page, per_page=count, error_out=False)
    
    entries = []
    for patient in patients.items:
        fhir_patient = FHIRMapper.patient_to_fhir(patient)
        entries.append({
            "fullUrl": f"/fhir/Patient/{patient.fhir_id}",
            "resource": fhir_patient
        })
    
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": patients.total,
        "entry": entries,
        "link": [
            {
                "relation": "self",
                "url": request.url
            }
        ]
    }
    
    return jsonify(bundle), 200


@bp.route('/Patient/<string:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    patient = Patient.query.filter_by(fhir_id=patient_id).first_or_404()
    fhir_patient = FHIRMapper.patient_to_fhir(patient)
    return jsonify(fhir_patient), 200


@bp.route('/Patient/<string:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    patient = Patient.query.filter_by(fhir_id=patient_id).first_or_404()
    
    try:
        fhir_patient = request.get_json()
        updated_patient = FHIRMapper.fhir_to_patient(fhir_patient)
        
        # Update fields
        patient.name = updated_patient.name
        patient.birth_date = updated_patient.birth_date
        patient.gender = updated_patient.gender
        patient.notes = updated_patient.notes
        
        db.session.commit()
        
        fhir_patient_response = FHIRMapper.patient_to_fhir(patient)
        return jsonify(fhir_patient_response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/Patient/<string:patient_id>', methods=['PATCH'])
@jwt_required()
def patch_patient(patient_id):
    patient = Patient.query.filter_by(fhir_id=patient_id).first_or_404()
    
    try:
        fhir_patient = request.get_json()
        
        # Update only provided fields
        if 'name' in fhir_patient:
            name_entry = fhir_patient.get("name", [{}])[0] if fhir_patient.get("name") else {}
            name = name_entry.get("text") or name_entry.get("family", "") + " " + name_entry.get("given", [""])[0]
            patient.name = name.strip() or patient.name
        
        if 'gender' in fhir_patient:
            patient.gender = fhir_patient['gender']
        
        if 'birthDate' in fhir_patient:
            patient.birth_date = datetime.fromisoformat(fhir_patient['birthDate'])
        
        if 'note' in fhir_patient:
            notes = fhir_patient['note']
            if notes:
                patient.notes = notes[0].get('text', patient.notes)
        
        db.session.commit()
        
        fhir_patient_response = FHIRMapper.patient_to_fhir(patient)
        return jsonify(fhir_patient_response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/Patient/<string:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    patient = Patient.query.filter_by(fhir_id=patient_id).first_or_404()
    
    # Delete related records first due to foreign key constraints
    from app.models import MedicalDocument, Observation, TestReport
    MedicalDocument.query.filter_by(patient_id=patient.id).delete()
    Observation.query.filter_by(patient_id=patient.id).delete()
    TestReport.query.filter_by(patient_id=patient.id).delete()
    
    db.session.delete(patient)
    db.session.commit()
    
    return '', 204


@bp.route('/Patient', methods=['POST'])
@jwt_required()
def create_patient():
    # Check if we've reached the maximum number of patient profiles
    from config import Config
    patient_count = Patient.query.count()
    if patient_count >= Config.MAX_PATIENT_PROFILES:
        return jsonify({
            'error': f'Maximum number of patient profiles ({Config.MAX_PATIENT_PROFILES}) reached'
        }), 400
    
    try:
        fhir_patient = request.get_json()
        new_patient = FHIRMapper.fhir_to_patient(fhir_patient)
        
        db.session.add(new_patient)
        db.session.commit()
        
        fhir_patient_response = FHIRMapper.patient_to_fhir(new_patient)
        return jsonify(fhir_patient_response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/Observation', methods=['GET'])
@jwt_required()
def search_observations():
    patient_id = request.args.get('patient')
    code = request.args.get('code')  # LOINC code
    date_from = request.args.get('date=ge')  # FHIR-style date filtering
    date_to = request.args.get('date=le')    # FHIR-style date filtering
    
    query = Observation.query
    
    if patient_id:
        # Handle both internal ID and FHIR ID
        patient = Patient.query.filter(
            (Patient.id == patient_id) | (Patient.fhir_id == patient_id)
        ).first()
        if patient:
            query = query.filter(Observation.patient_id == patient.id)
    
    if code:
        # Filter by biomarker that has the specified LOINC code
        from app.models import Biomarker, LOINCCode
        query = query.join(Biomarker).join(Biomarker.loinc).filter(
            LOINCCode.code == code
        )
    
    if date_from:
        date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        query = query.filter(Observation.effective_datetime >= date_from_obj)
    
    if date_to:
        date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        query = query.filter(Observation.effective_datetime <= date_to_obj)
    
    # Apply pagination
    page = request.args.get('page', 1, type=int)
    count = min(request.args.get('_count', 20, type=int), 100)
    
    observations = query.paginate(page=page, per_page=count, error_out=False)
    
    entries = []
    for observation in observations.items:
        fhir_observation = FHIRMapper.observation_to_fhir(observation)
        entries.append({
            "fullUrl": f"/fhir/Observation/{observation.fhir_id}",
            "resource": fhir_observation
        })
    
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": observations.total,
        "entry": entries,
        "link": [
            {
                "relation": "self",
                "url": request.url
            }
        ]
    }
    
    return jsonify(bundle), 200


@bp.route('/Observation/<string:observation_id>', methods=['GET'])
@jwt_required()
def get_observation(observation_id):
    observation = Observation.query.filter_by(fhir_id=observation_id).first_or_404()
    fhir_observation = FHIRMapper.observation_to_fhir(observation)
    return jsonify(fhir_observation), 200


@bp.route('/Observation', methods=['POST'])
@jwt_required()
def create_observation():
    try:
        fhir_observation = request.get_json()
        
        # Extract patient and report IDs from references
        subject_ref = fhir_observation.get('subject', {}).get('reference', '')
        if not subject_ref.startswith('Patient/'):
            return jsonify({'error': 'Invalid patient reference'}), 400
        
        patient_fhir_id = subject_ref.split('/')[1]
        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # For this implementation, we'll need to extract or create a report ID
        # In a real implementation, this would come from the FHIR resource or be created
        report_id = 1  # Placeholder - in real implementation, handle report reference properly
        
        new_observation = FHIRMapper.fhir_to_observation(fhir_observation, patient.id, report_id)
        
        db.session.add(new_observation)
        db.session.commit()
        
        fhir_observation_response = FHIRMapper.observation_to_fhir(new_observation)
        return jsonify(fhir_observation_response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/Observation/<string:observation_id>', methods=['PUT'])
@jwt_required()
def update_observation(observation_id):
    observation = Observation.query.filter_by(fhir_id=observation_id).first_or_404()
    
    try:
        fhir_observation = request.get_json()
        
        # Extract patient and report IDs from references
        subject_ref = fhir_observation.get('subject', {}).get('reference', '')
        if not subject_ref.startswith('Patient/'):
            return jsonify({'error': 'Invalid patient reference'}), 400
        
        patient_fhir_id = subject_ref.split('/')[1]
        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Update fields
        updated_observation = FHIRMapper.fhir_to_observation(fhir_observation, patient.id, observation.report_id)
        
        # Preserve the original ID
        updated_observation.id = observation.id
        updated_observation.fhir_id = observation_id
        
        db.session.merge(updated_observation)
        db.session.commit()
        
        fhir_observation_response = FHIRMapper.observation_to_fhir(updated_observation)
        return jsonify(fhir_observation_response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/Observation/<string:observation_id>', methods=['DELETE'])
@jwt_required()
def delete_observation(observation_id):
    observation = Observation.query.filter_by(fhir_id=observation_id).first_or_404()
    
    db.session.delete(observation)
    db.session.commit()
    
    return '', 204


@bp.route('/DiagnosticReport', methods=['GET'])
@jwt_required()
def search_reports():
    patient_id = request.args.get('patient')
    
    query = TestReport.query
    
    if patient_id:
        # Handle both internal ID and FHIR ID
        patient = Patient.query.filter(
            (Patient.id == patient_id) | (Patient.fhir_id == patient_id)
        ).first()
        if patient:
            query = query.filter(TestReport.patient_id == patient.id)
    
    # Apply pagination
    page = request.args.get('page', 1, type=int)
    count = min(request.args.get('_count', 20, type=int), 100)
    
    reports = query.paginate(page=page, per_page=count, error_out=False)
    
    entries = []
    for report in reports.items:
        fhir_report = FHIRMapper.report_to_fhir(report)
        entries.append({
            "fullUrl": f"/fhir/DiagnosticReport/{report.fhir_id}",
            "resource": fhir_report
        })
    
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": reports.total,
        "entry": entries,
        "link": [
            {
                "relation": "self",
                "url": request.url
            }
        ]
    }
    
    return jsonify(bundle), 200


@bp.route('/DiagnosticReport/<string:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    report = TestReport.query.filter_by(fhir_id=report_id).first_or_404()
    fhir_report = FHIRMapper.report_to_fhir(report)
    return jsonify(fhir_report), 200


@bp.route('/DiagnosticReport', methods=['POST'])
@jwt_required()
def create_report():
    try:
        fhir_report = request.get_json()
        
        # Extract patient ID from reference
        subject_ref = fhir_report.get('subject', {}).get('reference', '')
        if not subject_ref.startswith('Patient/'):
            return jsonify({'error': 'Invalid patient reference'}), 400
        
        patient_fhir_id = subject_ref.split('/')[1]
        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        new_report = FHIRMapper.fhir_to_report(fhir_report, patient.id)
        
        db.session.add(new_report)
        db.session.commit()
        
        fhir_report_response = FHIRMapper.report_to_fhir(new_report)
        return jsonify(fhir_report_response), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/DiagnosticReport/<string:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    report = TestReport.query.filter_by(fhir_id=report_id).first_or_404()
    
    try:
        fhir_report = request.get_json()
        
        # Extract patient ID from reference
        subject_ref = fhir_report.get('subject', {}).get('reference', '')
        if not subject_ref.startswith('Patient/'):
            return jsonify({'error': 'Invalid patient reference'}), 400
        
        patient_fhir_id = subject_ref.split('/')[1]
        patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Update fields
        updated_report = FHIRMapper.fhir_to_report(fhir_report, patient.id)
        
        # Preserve the original ID
        updated_report.id = report.id
        updated_report.fhir_id = report_id
        updated_report.patient_id = report.patient_id  # Don't change patient association
        
        db.session.merge(updated_report)
        db.session.commit()
        
        fhir_report_response = FHIRMapper.report_to_fhir(updated_report)
        return jsonify(fhir_report_response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/DiagnosticReport/<string:report_id>', methods=['DELETE'])
@jwt_required()
def delete_report(report_id):
    report = TestReport.query.filter_by(fhir_id=report_id).first_or_404()
    
    # Delete related observations first due to foreign key constraints
    Observation.query.filter_by(report_id=report.id).delete()
    
    db.session.delete(report)
    db.session.commit()
    
    return '', 204


@bp.route('/Bundle', methods=['GET'])
@jwt_required()
def get_bundle():
    patient_id = request.args.get('patient')
    bundle_type = request.args.get('type', 'collection')
    
    if not patient_id:
        return jsonify({'error': 'Patient ID is required'}), 400
    
    # Handle both internal ID and FHIR ID
    patient = Patient.query.filter(
        (Patient.id == patient_id) | (Patient.fhir_id == patient_id)
    ).first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    
    # Get all related resources for this patient
    fhir_resources = []
    
    # Add patient
    fhir_resources.append(FHIRMapper.patient_to_fhir(patient))
    
    # Add all observations for this patient
    observations = Observation.query.filter_by(patient_id=patient.id).all()
    for obs in observations:
        fhir_resources.append(FHIRMapper.observation_to_fhir(obs))
    
    # Add all reports for this patient
    reports = TestReport.query.filter_by(patient_id=patient.id).all()
    for rep in reports:
        fhir_resources.append(FHIRMapper.report_to_fhir(rep))
    
    # Create bundle
    bundle = FHIRMapper.create_bundle(fhir_resources, bundle_type)
    
    return jsonify(bundle), 200


@bp.route('/Bundle', methods=['POST'])
@jwt_required()
def post_bundle():
    """Import a complete patient bundle"""
    try:
        bundle = request.get_json()
        
        if bundle.get('resourceType') != 'Bundle':
            return jsonify({'error': 'Resource is not a Bundle'}), 400
        
        entries = bundle.get('entry', [])
        
        imported_resources = []
        
        for entry in entries:
            resource = entry.get('resource')
            if not resource:
                continue
                
            resource_type = resource.get('resourceType')
            
            if resource_type == 'Patient':
                # Create or update patient
                patient = FHIRMapper.fhir_to_patient(resource)
                
                # Check if patient already exists
                existing_patient = Patient.query.filter_by(fhir_id=resource.get('id')).first()
                if existing_patient:
                    # Update existing patient
                    existing_patient.name = patient.name
                    existing_patient.birth_date = patient.birth_date
                    existing_patient.gender = patient.gender
                    existing_patient.notes = patient.notes
                    db.session.merge(existing_patient)
                    imported_resources.append(existing_patient)
                else:
                    # Add new patient
                    db.session.add(patient)
                    imported_resources.append(patient)
            
            elif resource_type == 'DiagnosticReport':
                # Find the patient first
                subject_ref = resource.get('subject', {}).get('reference', '')
                if not subject_ref.startswith('Patient/'):
                    continue
                    
                patient_fhir_id = subject_ref.split('/')[1]
                patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
                if not patient:
                    continue
                
                # Create report
                report = FHIRMapper.fhir_to_report(resource, patient.id)
                
                # Check if report already exists
                existing_report = TestReport.query.filter_by(fhir_id=resource.get('id')).first()
                if existing_report:
                    # Update existing report
                    existing_report.patient_id = patient.id
                    existing_report.effective_datetime = report.effective_datetime
                    existing_report.status = report.status
                    existing_report.category = report.category
                    existing_report.conclusion = report.conclusion
                    existing_report.conclusion_code = report.conclusion_code
                    db.session.merge(existing_report)
                    imported_resources.append(existing_report)
                else:
                    # Add new report
                    db.session.add(report)
                    imported_resources.append(report)
            
            elif resource_type == 'Observation':
                # Find the patient first
                subject_ref = resource.get('subject', {}).get('reference', '')
                if not subject_ref.startswith('Patient/'):
                    continue
                    
                patient_fhir_id = subject_ref.split('/')[1]
                patient = Patient.query.filter_by(fhir_id=patient_fhir_id).first()
                if not patient:
                    continue
                
                # Find the report for this observation
                # For simplicity, we'll create a basic report if one doesn't exist
                # In a real implementation, this would be handled differently
                report = TestReport.query.filter_by(patient_id=patient.id).first()
                if not report:
                    report = TestReport(
                        patient_id=patient.id,
                        effective_datetime=datetime.utcnow(),
                        status="final",
                        category="laboratory"
                    )
                    db.session.add(report)
                
                # Create observation
                observation = FHIRMapper.fhir_to_observation(resource, patient.id, report.id)
                
                # Check if observation already exists
                existing_observation = Observation.query.filter_by(fhir_id=resource.get('id')).first()
                if existing_observation:
                    # Update existing observation
                    existing_observation.patient_id = patient.id
                    existing_observation.report_id = report.id
                    existing_observation.biomarker_id = observation.biomarker_id
                    existing_observation.effective_datetime = observation.effective_datetime
                    existing_observation.value = observation.value
                    existing_observation.status = observation.status
                    existing_observation.category = observation.category
                    existing_observation.unit = observation.unit
                    existing_observation.ref_min = observation.ref_min
                    existing_observation.ref_max = observation.ref_max
                    existing_observation.interpretation = observation.interpretation
                    existing_observation.notes = observation.notes
                    existing_observation.performer = observation.performer
                    existing_observation.specimen = observation.specimen
                    existing_observation.method = observation.method
                    db.session.merge(existing_observation)
                    imported_resources.append(existing_observation)
                else:
                    # Add new observation
                    db.session.add(observation)
                    imported_resources.append(observation)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully imported {len(imported_resources)} resources',
            'resources_imported': len(imported_resources)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400