from flask import Blueprint, request, jsonify, send_file, abort
from flask_jwt_extended import jwt_required
from app.models import MedicalDocument, Patient, TestReport
from app import db
from app.schemas import MedicalDocumentCreate, MedicalDocumentResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid


bp = Blueprint('documents', __name__)

# Configure allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Extract form data
        patient_id = request.form.get('patient_id', type=int)
        report_id = request.form.get('report_id', type=int)
        description = request.form.get('description', '')
        
        # Validate patient exists
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Validate report exists if provided
        if report_id:
            report = TestReport.query.get(report_id)
            if not report:
                return jsonify({'error': 'Report not found'}), 404
        
        # Secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Create file path
        patient_dir = os.path.join('data', 'patients', str(patient_id), 'documents')
        os.makedirs(patient_dir, exist_ok=True)
        filepath = os.path.join(patient_dir, unique_filename)
        
        # Save file
        file.save(filepath)
        
        # Create document record
        doc = MedicalDocument(
            patient_id=patient_id,
            report_id=report_id,
            filename=filename,
            filepath=filepath,
            file_type=filename.rsplit('.', 1)[1].lower(),
            file_size=os.path.getsize(filepath),
            description=description
        )
        
        db.session.add(doc)
        db.session.commit()
        
        return jsonify(MedicalDocumentResponse.from_orm(doc).dict()), 201
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Document already exists'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:doc_id>/download', methods=['GET'])
@jwt_required()
def download_document(doc_id):
    try:
        document = MedicalDocument.query.get_or_404(doc_id)
        
        if not os.path.exists(document.filepath):
            return jsonify({'error': 'File not found on disk'}), 404
        
        return send_file(document.filepath, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:doc_id>/preview', methods=['GET'])
@jwt_required()
def preview_document(doc_id):
    try:
        document = MedicalDocument.query.get_or_404(doc_id)
        
        if not os.path.exists(document.filepath):
            return jsonify({'error': 'File not found on disk'}), 404
        
        # For images, send the file directly
        if document.file_type.lower() in ['jpg', 'jpeg', 'png']:
            return send_file(document.filepath)
        else:
            # For PDFs and other files, return a placeholder or thumbnail
            return jsonify({
                'message': f'Preview not available for {document.file_type} files',
                'filename': document.filename,
                'size': document.file_size
            }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    try:
        document = MedicalDocument.query.get_or_404(doc_id)
        
        # Delete file from filesystem
        if os.path.exists(document.filepath):
            os.remove(document.filepath)
        
        # Delete database record
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'message': 'Document deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/', methods=['GET'])
@jwt_required()
def get_documents():
    try:
        patient_id = request.args.get('patient', type=int)
        report_id = request.args.get('report', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        query = MedicalDocument.query
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        if report_id:
            query = query.filter_by(report_id=report_id)
        
        documents = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'documents': [MedicalDocumentResponse.from_orm(doc).dict() for doc in documents.items],
            'total': documents.total,
            'pages': documents.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500