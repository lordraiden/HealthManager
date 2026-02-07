from flask import Blueprint, request, jsonify, session
from app.i18n import get_available_languages, get_text
from functools import wraps

bp = Blueprint('settings', __name__)

def login_required(f):
    """Decorator to require valid session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/api/v1/settings/language', methods=['GET'])
@login_required
def get_language():
    """Get current language setting"""
    lang = session.get('language', 'en')  # Default to English
    return jsonify({
        'language': lang,
        'available_languages': get_available_languages()
    })


@bp.route('/api/v1/settings/language', methods=['POST'])
@login_required
def set_language():
    """Set language preference"""
    data = request.get_json()
    lang = data.get('language')
    
    if not lang or lang not in ['en', 'es']:
        return jsonify({'error': 'Invalid language code. Use "en" or "es"'}), 400
    
    session['language'] = lang
    return jsonify({
        'message': get_text('settings_saved', lang),
        'language': lang
    })


@bp.route('/api/v1/translate/<key>', methods=['GET'])
@login_required
def translate(key):
    """Translate a specific text key"""
    lang = session.get('language', 'en')
    translated_text = get_text(key, lang)
    return jsonify({
        'original_key': key,
        'translated_text': translated_text,
        'language': lang
    })