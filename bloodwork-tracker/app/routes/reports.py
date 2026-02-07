from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import TestReport, Patient
from app import db
from app.schemas import TestReportCreate, TestReportUpdate, TestReportResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from datetime import datetime


bp = Blueprint('reports', __name__)


@bp.route('/', methods=['GET'])
@jwt_required()
def get_reports():
    try:
        patient_id = request.args.get('patient', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('_count', 20, type=int), 100)  # Using FHIR-style parameter
        
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
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/', methods=['POST'])
@jwt_required()
def create_report():
    try:
        report_data = TestReportCreate(**request.json)
        
        # Validate that patient exists
        patient = Patient.query.get(report_data.patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        report = TestReport(**report_data.dict())
        db.session.add(report)
        db.session.commit()
        
        return jsonify(TestReportResponse.from_orm(report).dict()), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Report already exists'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    try:
        report = TestReport.query.get_or_404(report_id)
        return jsonify(TestReportResponse.from_orm(report).dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    try:
        report = TestReport.query.get_or_404(report_id)
        report_update = TestReportUpdate(**request.json)
        
        update_data = report_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(report, field, value)
        
        db.session.commit()
        return jsonify(TestReportResponse.from_orm(report).dict()), 200
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:report_id>', methods=['DELETE'])
@jwt_required()
def delete_report(report_id):
    try:
        report = TestReport.query.get_or_404(report_id)
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'message': 'Report deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500