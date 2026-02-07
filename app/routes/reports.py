from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import TestReport, Patient, Observation
from app.schemas import TestReportCreate, TestReportUpdate, TestReportResponse
from app import db

bp = Blueprint('reports', __name__, url_prefix='/api/v1/reports')


@bp.route('', methods=['GET'])
@jwt_required()
def get_reports():
    patient_id = request.args.get('patient', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('_count', 20, type=int), 100)  # Using FHIR-style _count
    
    query = TestReport.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    reports = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'reports': [TestReportResponse.from_orm(r).dict() for r in reports.items],
        'total': reports.total,
        'pages': reports.pages,
        'current_page': page
    }), 200


@bp.route('/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    report = TestReport.query.get_or_404(report_id)
    return jsonify(TestReportResponse.from_orm(report).dict()), 200


@bp.route('', methods=['POST'])
@jwt_required()
def create_report():
    try:
        data = request.get_json()
        report_data = TestReportCreate(**data)
        
        # Verify patient exists
        patient = Patient.query.get(report_data.patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        report = TestReport(
            patient_id=report_data.patient_id,
            effective_datetime=report_data.effective_datetime,
            status=report_data.status,
            category=report_data.category,
            conclusion=report_data.conclusion,
            conclusion_code=report_data.conclusion_code
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify(TestReportResponse.from_orm(report).dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    report = TestReport.query.get_or_404(report_id)
    
    try:
        data = request.get_json()
        report_update = TestReportUpdate(**data)
        
        for field, value in report_update.dict(exclude_unset=True).items():
            setattr(report, field, value)
        
        db.session.commit()
        
        return jsonify(TestReportResponse.from_orm(report).dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:report_id>', methods=['DELETE'])
@jwt_required()
def delete_report(report_id):
    report = TestReport.query.get_or_404(report_id)
    
    # Delete related observations first due to foreign key constraints
    Observation.query.filter_by(report_id=report_id).delete()
    
    # Then delete the report
    db.session.delete(report)
    db.session.commit()
    
    return jsonify({'message': 'Report deleted successfully'}), 200