import jwt
import datetime
import re
from flask import Blueprint, request, jsonify, current_app
from models import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_token(email):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
            'iat': datetime.datetime.utcnow(),
            'sub': email
        }
        return jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
    except Exception as e:
        print(f"Token generation error: {str(e)}")
        raise Exception(f"Error generating token: {str(e)}")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=["HS256"])
            return f({'id': data['sub'], 'email': data['sub']}, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': f'Error processing token: {str(e)}'}), 401
    return decorated

@auth_bp.route('/get_token', methods=['POST'])
def get_token():
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
            
        email = data['email']
        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        # Generate token
        token = generate_token(email)
        return jsonify({
            'token': token,
            'email': email
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        token = data.get('token')
        if not token:
            return jsonify({'error': 'Token is required'}), 400

        # Clean the token
        token = token.strip()
        
        try:
            # Verify token is valid JWT
            data = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=["HS256"])
            return jsonify({
                'message': 'Login successful',
                'email': data['sub']
            }), 200
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token format'}), 401

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
