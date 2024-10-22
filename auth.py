import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from models import User, db
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def generate_token(user_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        current_app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['sub']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/get_token', methods=['POST'])
def get_token():
    email = request.json.get('email')
    if not email:
        return jsonify({'message': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        return jsonify({'message': 'User already exists'}), 400

    new_user = User(email=email)
    token = generate_token(new_user.id)
    new_user.token = token
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'token': token}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    token = request.json.get('token')
    if not token:
        return jsonify({'message': 'Token is required'}), 400

    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({'message': 'Invalid token'}), 401

    return jsonify({'message': 'Login successful', 'questionnaire_completed': user.questionnaire_completed}), 200

@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello, {current_user.email}! This is a protected route.'})
