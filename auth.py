import jwt
import datetime
import re
from flask import Blueprint, request, jsonify, current_app
from models import User, db
from functools import wraps
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def generate_token(user_id):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        ).replace('|', '')
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
            current_user = User.query.filter_by(id=data['sub']).first()
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': f'Error processing token: {str(e)}'}), 401
        return f(current_user, *args, **kwargs)
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

        # Check for existing user first
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        # Create new user with default values
        new_user = User(
            email=email,
            questionnaire_completed=False,  # Explicitly set to False for new users
            user_type=None,
            learning_difficulty=None,
            difficulty_details=None
        )
        
        try:
            db.session.add(new_user)
            db.session.flush()  # Get the ID without committing
            token = generate_token(new_user.id)
            new_user.token = token
            db.session.commit()
            return jsonify({
                'token': token,
                'questionnaire_completed': False,  # Include flag in response
                'redirect': '/questionnaire'  # Add redirect path
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

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
        token = token.strip().replace('\s+', '')
        
        try:
            # Verify token is valid JWT
            decoded = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=["HS256"])
            user = User.query.filter_by(token=token).first()
            
            if not user:
                return jsonify({'error': 'User not found with this token'}), 401

            # Return questionnaire state and appropriate redirect
            redirect_path = '/dashboard' if user.questionnaire_completed else '/questionnaire'
            
            return jsonify({
                'message': 'Login successful',
                'questionnaire_completed': user.questionnaire_completed,
                'redirect': redirect_path,
                'user_type': user.user_type
            }), 200
            
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token format'}), 401

    except SQLAlchemyError as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@auth_bp.route('/check_questionnaire_status', methods=['GET'])
@token_required
def check_questionnaire_status(current_user):
    try:
        return jsonify({
            'questionnaire_completed': current_user.questionnaire_completed,
            'redirect': '/dashboard' if current_user.questionnaire_completed else '/questionnaire'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
