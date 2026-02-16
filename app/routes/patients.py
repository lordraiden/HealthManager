from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Patient, TestReport, Observation, MedicalDocument
from app.schemas import PatientCreate, PatientUpdate, PatientResponse
from app import db
from datetime import datetime
from config import Config

bp = Blueprint('patients', __name__, url_prefix='/api/v1/patients')


def _delete_patient_related_records(patient_id):
    """
    Delete all related records for a patient to satisfy foreign key constraints.
    
    Args:
        patient_id (int): ID of the patient whose related records should be deleted
    """
    # Delete medical documents
    MedicalDocument.query.filter_by(patient_id=patient_id).delete()
    
    # Delete observations
    Observation.query.filter_by(patient_id=patient_id).delete()
    
    # Delete test reports
    TestReport.query.filter_by(patient_id=patient_id).delete()


@bp.route('', methods=['GET'])
@jwt_required()
def get_patients():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    patients = Patient.query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'patients': [PatientResponse.from_orm(p).dict() for p in patients.items],
        'total': patients.total,
        'pages': patients.pages,
        'current_page': page
    }), 200


@bp.route('/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return jsonify(PatientResponse.from_orm(patient).dict()), 200


@bp.route('', methods=['POST'])
@jwt_required()
def create_patient():
    # Check if we've reached the maximum number of patient profiles
    patient_count = Patient.query.count()
    if patient_count >= Config.MAX_PATIENT_PROFILES:
        return jsonify({
            'error': f'Maximum number of patient profiles ({Config.MAX_PATIENT_PROFILES}) reached'
        }), 400
    
    try:
        data = request.get_json()
        patient_data = PatientCreate(**data)
        
        patient = Patient(
            name=patient_data.name,
            birth_date=patient_data.birth_date,
            gender=patient_data.gender,
            notes=patient_data.notes
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify(PatientResponse.from_orm(patient).dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        data = request.get_json()
        patient_update = PatientUpdate(**data)
        
        for field, value in patient_update.dict(exclude_unset=True).items():
            setattr(patient, field, value)
        
        patient.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify(PatientResponse.from_orm(patient).dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:patient_id>', methods=['PATCH'])
@jwt_required()
def patch_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    try:
        data = request.get_json()
        patient_update = PatientUpdate(**data)
        
        for field, value in patient_update.dict(exclude_unset=True).items():
            setattr(patient, field, value)
        
        patient.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify(PatientResponse.from_orm(patient).dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Delete related records first due to foreign key constraints
    _delete_patient_related_records(patient_id)
    
    # Finally delete the patient
    db.session.delete(patient)
    db.session.commit()
    
    return jsonify({'message': 'Patient deleted successfully'}), 200