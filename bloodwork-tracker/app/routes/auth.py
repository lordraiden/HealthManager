from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.models import User
from app import db
from app.schemas import LoginRequest, UserCreate
from pydantic import ValidationError
from werkzeug.security import check_password_hash
import datetime


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['POST'])
def login():
    try:
        login_data = LoginRequest(**request.json)
        
        user = User.query.filter_by(username=login_data.username).first()
        
        if user and user.check_password(login_data.password):
            # Update last login
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'bearer',
                'user_id': user.id,
                'username': user.username
            }), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    except ValidationError as e:
        return jsonify({'errors': e.errors()}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In a real application, you might want to blacklist the token
    return jsonify({'message': 'Logged out successfully'}), 200


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    new_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': new_token}), 200


@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not user.check_password(old_password):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200


@bp.route('/session', methods=['GET'])
@jwt_required()
def get_session():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'last_login': user.last_login.isoformat() if user.last_login else None
    }), 200


@bp.route('/session/<int:session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    # In a real application, you would implement session blacklisting
    # For now, we'll just return a success message
    return jsonify({'message': f'Session {session_id} terminated'}), 200