from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Observation, Patient, TestReport, Biomarker
from app import db
from app.schemas import ObservationCreate, ObservationUpdate, ObservationResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


bp = Blueprint('observations', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_observations():
    try:
        patient_id = request.args.get('patient', type=int)
        code = request.args.get('code')  # LOINC code
        date_from = request.args.get('date_ge')  # Format: YYYY-MM-DD
        date_to = request.args.get('date_le')   # Format: YYYY-MM-DD
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        query = Observation.query
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        if code:
            # Join with biomarker to filter by LOINC code
            query = query.join(Biomarker).filter(Biomarker.loinc_code.has(code=code))
        
        if date_from:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Observation.effective_datetime >= date_from_obj)
        
        if date_to:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Observation.effective_datetime <= date_to_obj)
        
        observations = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'observations': [ObservationResponse.from_orm(obs).dict() for obs in observations.items],
            'total': observations.total,
            'pages': observations.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/', methods=['POST'])
@jwt_required()
def create_observation():
    try:
        observation_data = ObservationCreate(**request.json)
        
        # Validate that patient, report, and biomarker exist
        patient = Patient.query.get(observation_data.patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        report = TestReport.query.get(observation_data.report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        biomarker = Biomarker.query.get(observation_data.biomarker_id)
        if not biomarker:
            return jsonify({'error': 'Biomarker not found'}), 404
        
        observation = Observation(**observation_data.dict())
        
        # Set interpretation if not provided
        if not observation.interpretation:
            if observation.ref_min is not None and observation.ref_max is not None:
                if observation.value < observation.ref_min:
                    observation.interpretation = 'L'  # Low
                elif observation.value > observation.ref_max:
                    observation.interpretation = 'H'  # High
                else:
                    observation.interpretation = 'N'  # Normal
        
        db.session.add(observation)
        db.session.commit()
        
        return jsonify(ObservationResponse.from_orm(observation).dict()), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Observation already exists'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:obs_id>', methods=['GET'])
@jwt_required()
def get_observation(obs_id):
    try:
        observation = Observation.query.get_or_404(obs_id)
        return jsonify(ObservationResponse.from_orm(observation).dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:obs_id>', methods=['PUT'])
@jwt_required()
def update_observation(obs_id):
    try:
        observation = Observation.query.get_or_404(obs_id)
        observation_update = ObservationUpdate(**request.json)
        
        update_data = observation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(observation, field, value)
        
        # Update interpretation if value or reference ranges changed
        if ('value' in update_data or 'ref_min' in update_data or 'ref_max' in update_data) and \
           observation.ref_min is not None and observation.ref_max is not None:
            if observation.value < observation.ref_min:
                observation.interpretation = 'L'  # Low
            elif observation.value > observation.ref_max:
                observation.interpretation = 'H'  # High
            else:
                observation.interpretation = 'N'  # Normal
        
        db.session.commit()
        return jsonify(ObservationResponse.from_orm(observation).dict()), 200
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:obs_id>', methods=['DELETE'])
@jwt_required()
def delete_observation(obs_id):
    try:
        observation = Observation.query.get_or_404(obs_id)
        db.session.delete(observation)
        db.session.commit()
        
        return jsonify({'message': 'Observation deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500