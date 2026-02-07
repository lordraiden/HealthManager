from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Observation, Patient, TestReport, Biomarker
from app.schemas import ObservationCreate, ObservationUpdate, ObservationResponse
from app import db

bp = Blueprint('observations', __name__, url_prefix='/api/v1/observations')


@bp.route('', methods=['GET'])
@jwt_required()
def get_observations():
    patient_id = request.args.get('patient', type=int)
    loinc_code = request.args.get('code')  # LOINC code filter
    date_from = request.args.get('date_ge')  # FHIR-style date filtering: ge=date
    date_to = request.args.get('date_le')    # FHIR-style date filtering: le=date
    
    query = Observation.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    if loinc_code:
        # Filter by biomarker that has the specified LOINC code
        query = query.join(Biomarker).join(Biomarker.loinc).filter(
            Biomarker.loinc.has(code=loinc_code)
        )
    
    if date_from:
        from datetime import datetime
        date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        query = query.filter(Observation.effective_datetime >= date_from_obj)
    
    if date_to:
        from datetime import datetime
        date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        query = query.filter(Observation.effective_datetime <= date_to_obj)
    
    # Apply pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    observations = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'observations': [ObservationResponse.from_orm(obs).dict() for obs in observations.items],
        'total': observations.total,
        'pages': observations.pages,
        'current_page': page
    }), 200


@bp.route('/<int:observation_id>', methods=['GET'])
@jwt_required()
def get_observation(observation_id):
    observation = Observation.query.get_or_404(observation_id)
    return jsonify(ObservationResponse.from_orm(observation).dict()), 200


@bp.route('', methods=['POST'])
@jwt_required()
def create_observation():
    try:
        data = request.get_json()
        observation_data = ObservationCreate(**data)
        
        # Verify patient exists
        patient = Patient.query.get(observation_data.patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Verify report exists
        report = TestReport.query.get(observation_data.report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Verify biomarker exists
        biomarker = Biomarker.query.get(observation_data.biomarker_id)
        if not biomarker:
            return jsonify({'error': 'Biomarker not found'}), 404
        
        observation = Observation(
            patient_id=observation_data.patient_id,
            report_id=observation_data.report_id,
            biomarker_id=observation_data.biomarker_id,
            effective_datetime=observation_data.effective_datetime,
            value=observation_data.value,
            status=observation_data.status,
            category=observation_data.category,
            unit=observation_data.unit,
            ref_min=observation_data.ref_min,
            ref_max=observation_data.ref_max,
            interpretation=observation_data.interpretation,
            notes=observation_data.notes,
            performer=observation_data.performer,
            specimen=observation_data.specimen,
            method=observation_data.method
        )
        
        db.session.add(observation)
        db.session.commit()
        
        return jsonify(ObservationResponse.from_orm(observation).dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:observation_id>', methods=['PUT'])
@jwt_required()
def update_observation(observation_id):
    observation = Observation.query.get_or_404(observation_id)
    
    try:
        data = request.get_json()
        observation_update = ObservationUpdate(**data)
        
        for field, value in observation_update.dict(exclude_unset=True).items():
            setattr(observation, field, value)
        
        db.session.commit()
        
        return jsonify(ObservationResponse.from_orm(observation).dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:observation_id>', methods=['DELETE'])
@jwt_required()
def delete_observation(observation_id):
    observation = Observation.query.get_or_404(observation_id)
    
    db.session.delete(observation)
    db.session.commit()
    
    return jsonify({'message': 'Observation deleted successfully'}), 200