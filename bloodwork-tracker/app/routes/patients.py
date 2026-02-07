from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Patient, User
from app import db
from app.schemas import PatientCreate, PatientUpdate, PatientResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
import uuid


bp = Blueprint('patients', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_patients():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        
        patients = Patient.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'patients': [PatientResponse.from_orm(p).dict() for p in patients.items],
            'total': patients.total,
            'pages': patients.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/', methods=['POST'])
@jwt_required()
def create_patient():
    try:
        patient_data = PatientCreate(**request.json)
        
        # Check if we've reached the max patient limit (4)
        patient_count = Patient.query.count()
        if patient_count >= 4:
            return jsonify({'error': 'Maximum number of patients (4) reached'}), 400
        
        patient = Patient(**patient_data.dict())
        db.session.add(patient)
        db.session.commit()
        
        return jsonify(PatientResponse.from_orm(patient).dict()), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Patient already exists'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        return jsonify(PatientResponse.from_orm(patient).dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        patient_update = PatientUpdate(**request.json)
        
        update_data = patient_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)
        
        db.session.commit()
        return jsonify(PatientResponse.from_orm(patient).dict()), 200
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:patient_id>', methods=['PATCH'])
@jwt_required()
def patch_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        for field, value in request.json.items():
            if hasattr(patient, field):
                setattr(patient, field, value)
        
        db.session.commit()
        return jsonify(PatientResponse.from_orm(patient).dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        db.session.delete(patient)
        db.session.commit()
        
        return jsonify({'message': 'Patient deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500