from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.models import MedicalDocument, Patient, TestReport
from app.schemas import MedicalDocumentCreate, MedicalDocumentResponse
from app import db
import os
from datetime import datetime
import uuid

bp = Blueprint('documents', __name__, url_prefix='/api/v1/documents')


def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


@bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get form data
    patient_id = request.form.get('patient_id', type=int)
    report_id = request.form.get('report_id', type=int)
    description = request.form.get('description', '')
    
    if not patient_id:
        return jsonify({'error': 'Patient ID is required'}), 400
    
    # Verify patient exists
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    
    # Verify report exists if provided
    if report_id:
        report = TestReport.query.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
    
    # Validate file
    from config import Config
    if not allowed_file(file.filename, Config.ALLOWED_FILE_TYPES):
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(Config.ALLOWED_FILE_TYPES)}'}), 400
    
    if len(file.read()) > Config.FILE_UPLOAD_MAX_SIZE:
        return jsonify({'error': f'File too large. Maximum size: {Config.FILE_UPLOAD_MAX_SIZE} bytes'}), 400
    
    file.seek(0)  # Reset file pointer after reading for size check
    
    # Generate secure filename
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
    
    # Create patient-specific directory
    patient_dir = os.path.join(current_app.root_path, 'data', 'patients', str(patient_id), 'documents')
    os.makedirs(patient_dir, exist_ok=True)
    
    filepath = os.path.join(patient_dir, unique_filename)
    
    # Save file
    file.save(filepath)
    
    # Create document record
    file_size = os.path.getsize(filepath)
    document = MedicalDocument(
        patient_id=patient_id,
        filename=original_filename,
        filepath=filepath,
        file_type=file_ext,
        file_size=file_size,
        report_id=report_id,
        description=description
    )
    
    db.session.add(document)
    db.session.commit()
    
    return jsonify(MedicalDocumentResponse.from_orm(document).dict()), 201


@bp.route('/<int:document_id>/download', methods=['GET'])
@jwt_required()
def download_document(document_id):
    document = MedicalDocument.query.get_or_404(document_id)
    
    if not os.path.exists(document.filepath):
        return jsonify({'error': 'File not found on disk'}), 404
    
    return send_file(document.filepath, as_attachment=True)


@bp.route('/<int:document_id>/preview', methods=['GET'])
@jwt_required()
def preview_document(document_id):
    document = MedicalDocument.query.get_or_404(document_id)
    
    if not os.path.exists(document.filepath):
        return jsonify({'error': 'File not found on disk'}), 404
    
    # For images, send the file directly
    # For PDFs, might need special handling depending on frontend needs
    return send_file(document.filepath)


@bp.route('/<int:document_id>', methods=['DELETE'])
@jwt_required()
def delete_document(document_id):
    document = MedicalDocument.query.get_or_404(document_id)
    
    # Delete the physical file
    if os.path.exists(document.filepath):
        os.remove(document.filepath)
    
    # Delete the database record
    db.session.delete(document)
    db.session.commit()
    
    return jsonify({'message': 'Document deleted successfully'}), 200


@bp.route('', methods=['GET'])
@jwt_required()
def get_documents():
    patient_id = request.args.get('patient', type=int)
    report_id = request.args.get('report', type=int)
    
    query = MedicalDocument.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    if report_id:
        query = query.filter_by(report_id=report_id)
    
    # Apply pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    documents = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'documents': [MedicalDocumentResponse.from_orm(doc).dict() for doc in documents.items],
        'total': documents.total,
        'pages': documents.pages,
        'current_page': page
    }), 200