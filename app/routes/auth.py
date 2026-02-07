from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token, 
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app.schemas import LoginRequest, UserCreate, UserResponse
from app import db
from datetime import datetime
import uuid

bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


# Blacklist for revoked tokens
blacklisted_tokens = set()


@bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        login_request = LoginRequest(**data)
        
        user = User.query.filter_by(username=login_request.username).first()
        
        if user and check_password_hash(user.password_hash, login_request.password):
            # Update last login
            user.last_login = datetime.now()
            db.session.commit()
            
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'bearer',
                'user': UserResponse.from_orm(user).dict()
            }), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    blacklisted_tokens.add(jti)
    return jsonify({'message': 'Successfully logged out'}), 200


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
    
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not check_password_hash(user.password_hash, old_password):
        return jsonify({'error': 'Old password is incorrect'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200


@bp.route('/session', methods=['GET'])
@jwt_required()
def get_session():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': UserResponse.from_orm(user).dict()}), 200


@bp.route('/session/<int:session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    # In a real implementation, we would manage active sessions
    # For now, just return success
    return jsonify({'message': 'Session terminated successfully'}), 200


# Initialize default admin user if none exists
def init_default_user():
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            email='admin@example.com',
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()