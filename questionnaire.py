from flask import Blueprint, request, jsonify
from auth import token_required
from datetime import datetime

questionnaire_bp = Blueprint('questionnaire', __name__)

def classify_user(responses):
    scores = {
        'estructurado': 0,
        'explorador': 0,
        'intensivo': 0
    }
    
    # Análisis temporal (20 puntos)
    if responses['study_time'] == 'A':
        scores['estructurado'] += 10
    elif responses['study_time'] == 'C':
        scores['intensivo'] += 10
    else:
        scores['explorador'] += 10
    
    if responses['session_duration'] == 'B':
        scores['estructurado'] += 5
    elif responses['session_duration'] == 'C':
        scores['intensivo'] += 5
    else:
        scores['explorador'] += 5
    
    if responses['learning_pace'] == 'A':
        scores['estructurado'] += 5
    elif responses['learning_pace'] == 'C':
        scores['intensivo'] += 5
    else:
        scores['explorador'] += 5
    
    # Análisis metodológico (30 puntos)
    if responses['learning_style'] == 'A':
        scores['estructurado'] += 10
    elif responses['learning_style'] == 'B':
        scores['explorador'] += 10
    else:
        scores['intensivo'] += 10
    
    if responses['content_format'] == 'A':
        scores['estructurado'] += 5
    elif responses['content_format'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5
    
    if responses['feedback_preference'] == 'A':
        scores['estructurado'] += 5
    elif responses['feedback_preference'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5
    
    # Análisis motivacional (25 puntos)
    if responses['learning_goals'] == 'A':
        scores['estructurado'] += 5
    elif responses['learning_goals'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5
    
    if responses['motivators'] == 'A':
        scores['estructurado'] += 5
    elif responses['motivators'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5
    
    if responses['challenges'] == 'A':
        scores['estructurado'] += 5
    elif responses['challenges'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5
    
    # Análisis de contenido (25 puntos)
    if responses['interest_areas'] == 'A':
        scores['estructurado'] += 5
    elif responses['interest_areas'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5
    
    if responses['experience_level'] == 'B':
        scores['estructurado'] += 5
    elif responses['experience_level'] == 'C':
        scores['intensivo'] += 5
    else:
        scores['explorador'] += 5
    
    if responses['learning_tools'] == 'A':
        scores['estructurado'] += 5
    elif responses['learning_tools'] == 'B':
        scores['explorador'] += 5
    else:
        scores['intensivo'] += 5

    profile_type = max(scores.items(), key=lambda x: x[1])[0]
    user_type_mapping = {
        'estructurado': 'ESTRUCTURADO',
        'explorador': 'EXPLORADOR',
        'intensivo': 'INTENSIVO'
    }
    
    return user_type_mapping[profile_type]

@questionnaire_bp.route('/submit_questionnaire', methods=['POST'])
@token_required
def submit_questionnaire(current_user):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = [
            'study_time', 'session_duration', 'learning_pace',
            'learning_style', 'content_format', 'feedback_preference',
            'learning_goals', 'motivators', 'challenges',
            'interest_areas', 'experience_level', 'learning_tools'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        # Classify user type
        user_type = classify_user(data)
        
        # Return the questionnaire data and user type for frontend storage
        questionnaire_data = {
            'user_id': current_user['id'],
            'user_type': user_type,
            'responses': data,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'message': 'Questionnaire processed successfully',
            'questionnaire_data': questionnaire_data
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error processing questionnaire: {str(e)}'}), 500

@questionnaire_bp.route('/get_user_profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    return jsonify({
        'message': 'Profile data should be retrieved from localStorage',
        'email': current_user['email']
    }), 200
