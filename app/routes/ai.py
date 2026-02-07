from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.ai_provider import get_ai_provider, generate_fhir_context
from app.schemas import AIConsultRequest, AIConsultResponse
from app import db
from datetime import datetime
from config import Config

bp = Blueprint('ai', __name__, url_prefix='/api/v1/ai')


@bp.route('/consult', methods=['GET'])
@jwt_required()
def get_consult_form():
    """Return the AI consultation form/UI"""
    return jsonify({
        'providers': [
            {'name': 'mock', 'display': 'Simulado (prueba)'},
            {'name': 'local', 'display': 'Local (Ollama/LMStudio)'},
            {'name': 'openai', 'display': 'OpenAI'}
        ],
        'context_types': [
            {'name': 'fhir_bundle', 'display': 'Datos FHIR completos'},
            {'name': 'text_summary', 'display': 'Resumen de texto'},
            {'name': 'raw_data', 'display': 'Datos sin procesar'}
        ]
    }), 200


@bp.route('/consult', methods=['POST'])
@jwt_required()
def ai_consult():
    """Handle AI consultation request"""
    try:
        data = request.get_json()
        ai_request = AIConsultRequest(**data)
        
        # Determine which provider to use based on configuration and request
        provider_name = ai_request.provider
        if provider_name == 'local':
            # Use either Ollama or LMStudio based on config
            if Config.AI_PROVIDER in ['ollama', 'lmstudio']:
                provider_name = Config.AI_PROVIDER
            else:
                provider_name = 'mock'  # fallback
        
        # Prepare context based on context_type
        context = {}
        patient_id = data.get('patient_id')  # Expect patient_id in the request
        
        if patient_id:
            context = generate_fhir_context(patient_id)
        
        # Check if sending to cloud is enabled
        if provider_name == 'openai' and not Config.AI_SEND_TO_CLOUD:
            return jsonify({
                'error': 'Sending data to cloud providers is disabled. Please enable AI_SEND_TO_CLOUD in configuration.'
            }), 400
        
        # Get the AI provider
        provider_kwargs = {}
        if provider_name == 'openai':
            provider_kwargs['api_key'] = Config.OPENAI_API_KEY
            provider_kwargs['model'] = Config.OLLAMA_MODEL  # This uses the OLLAMA_MODEL config var for OpenAI
        elif provider_name == 'ollama':
            provider_kwargs['base_url'] = Config.OLLAMA_BASE_URL
            provider_kwargs['model'] = Config.OLLAMA_MODEL
        elif provider_name == 'lmstudio':
            provider_kwargs['base_url'] = Config.LMSTUDIO_BASE_URL
        
        provider = get_ai_provider(provider_name, **provider_kwargs)
        
        # Generate response based on context type
        prompt = ai_request.question
        if ai_request.context_type == 'fhir_bundle':
            prompt += f"\n\nDatos del paciente: {context.get('fhir_bundle', {})}"
        elif ai_request.context_type == 'text_summary':
            prompt += f"\n\nResumen de datos: {context.get('text_summary', '')}"
        elif ai_request.context_type == 'raw_data':
            prompt += f"\n\nDatos sin procesar: {context}"
        
        response = provider.generate_response(prompt, context)
        
        # Create response
        ai_response = AIConsultResponse(
            response=response,
            provider_used=provider.get_name(),
            timestamp=datetime.utcnow()
        )
        
        return jsonify(ai_response.dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/providers', methods=['GET'])
@jwt_required()
def list_providers():
    """List available AI providers"""
    return jsonify([
        {'name': 'mock', 'display': 'Proveedor simulado (prueba)', 'type': 'local'},
        {'name': 'ollama', 'display': 'Ollama (local)', 'type': 'local'},
        {'name': 'lmstudio', 'display': 'LM Studio (local)', 'type': 'local'},
        {'name': 'openai', 'display': 'OpenAI (cloud)', 'type': 'cloud'}
    ]), 200