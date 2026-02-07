from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.ai_provider import AIProviderFactory
from app.services.fhir_mapper import generate_fhir_context
from app import db
import time


bp = Blueprint('ai', __name__)


@bp.route('/consult', methods=['GET'])
@jwt_required()
def get_ai_form():
    """Return the AI consultation form UI"""
    # This would normally render a template, but returning JSON for API consistency
    return jsonify({
        'message': 'AI Consultation Endpoint',
        'providers': AIProviderFactory.get_available_providers(),
        'instructions': 'Send POST request to /api/v1/ai/consult with question and provider'
    }), 200


@bp.route('/consult', methods=['POST'])
@jwt_required()
def ai_consult():
    """Handle AI consultation request"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        provider_name = data.get('provider', 'mock')
        context_type = data.get('context_type', 'fhir_bundle')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Get patient ID if specified
        patient_id = data.get('patient_id')
        
        # Generate context based on type
        context = {}
        if patient_id and context_type in ['fhir_bundle', 'text_summary']:
            context = generate_fhir_context(patient_id)
        
        # Get AI provider
        provider = AIProviderFactory.get_provider(provider_name)
        if not provider:
            return jsonify({'error': f'Provider {provider_name} not available'}), 400
        
        # Prepare prompt
        if context_type == 'fhir_bundle' and context:
            prompt = f"""
            Question: {question}
            
            Patient Data (FHIR Format):
            {context.get('text_summary', '')}
            
            Please analyze the patient's medical data and provide insights based on the question above.
            IMPORTANT: This is for informational purposes only. Always consult with a healthcare professional for medical advice.
            """
        elif context_type == 'text_summary' and context:
            prompt = f"""
            Question: {question}
            
            Patient Data Summary:
            {context.get('text_summary', '')}
            
            Please analyze the patient's medical data and provide insights based on the question above.
            IMPORTANT: This is for informational purposes only. Always consult with a healthcare professional for medical advice.
            """
        else:
            prompt = f"""
            Question: {question}
            
            Please provide general information based on the question above.
            IMPORTANT: This is for informational purposes only. Always consult with a healthcare professional for medical advice.
            """
        
        # Track start time for processing time calculation
        start_time = time.time()
        
        # Generate response
        response = provider.generate_response(prompt, context)
        
        processing_time = time.time() - start_time
        
        return jsonify({
            'question': question,
            'answer': response,
            'provider_used': provider_name,
            'context_type': context_type,
            'processing_time': round(processing_time, 2),
            'patient_id': patient_id
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/providers', methods=['GET'])
@jwt_required()
def list_providers():
    """List all available AI providers"""
    try:
        providers = AIProviderFactory.get_available_providers()
        return jsonify({
            'providers': providers,
            'default_provider': 'mock'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500