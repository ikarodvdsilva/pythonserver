import jwt
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
from models import User

def generate_token(user_id, role):
    """Gera um token JWT para o usuário"""
    payload = {
        'exp': datetime.utcnow() + timedelta(days=1),
        'iat': datetime.utcnow(),
        'sub': user_id,
        'role': role
    }
    return jwt.encode(
        payload,
        current_app.config.get('JWT_SECRET_KEY'),
        algorithm='HS256'
    )

def token_required(f):
    """Decorator para verificar se o token JWT é válido"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(
                token, 
                current_app.config.get('JWT_SECRET_KEY'),
                algorithms=['HS256']
            )
            current_user_id = data['sub']
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user_id, *args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(
                token, 
                current_app.config.get('JWT_SECRET_KEY'),
                algorithms=['HS256']
            )
            if data['role'] != 'admin':
                return jsonify({'message': 'Admin privileges required!'}), 403
            current_user_id = data['sub']
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
            
        return f(current_user_id, *args, **kwargs)
    
    return decorated
