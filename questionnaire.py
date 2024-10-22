from flask import Blueprint, request, jsonify
from models import User, QuestionnaireResponse, db
from auth import token_required

questionnaire_bp = Blueprint('questionnaire', __name__)

@questionnaire_bp.route('/submit_questionnaire', methods=['POST'])
@token_required
def submit_questionnaire(current_user):
    data = request.json
    
    # Validate data
    required_fields = ['question1', 'question2', 'question3', 'question4', 'question5', 'question6']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing field: {field}'}), 400

    # Create new questionnaire response
    new_response = QuestionnaireResponse(
        user_id=current_user.id,
        question1=data['question1'],
        question2=data['question2'],
        question3=data['question3'],
        question4=data['question4'],
        question5=data['question5'],
        question6=','.join(data['question6'])  # Assuming question6 is a list of selected options
    )
    
    db.session.add(new_response)
    
    # Determine user type based on responses
    user_type = determine_user_type(data)
    current_user.user_type = user_type
    current_user.questionnaire_completed = True
    
    db.session.commit()
    
    return jsonify({'message': 'Questionnaire submitted successfully', 'user_type': user_type}), 200

def determine_user_type(responses):
    # Simple logic to determine user type
    # This can be expanded with more sophisticated classification algorithms
    if responses['question4'] >= 8:
        return 'A'
    elif responses['question4'] >= 5:
        return 'B'
    else:
        return 'C'

@questionnaire_bp.route('/get_user_profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    if not current_user.questionnaire_completed:
        return jsonify({'message': 'Questionnaire not completed'}), 400

    questionnaire = QuestionnaireResponse.query.filter_by(user_id=current_user.id).first()
    
    profile = {
        'email': current_user.email,
        'user_type': current_user.user_type,
        'questionnaire_responses': {
            'study_time': questionnaire.question1,
            'concentration_span': questionnaire.question2,
            'learning_style': questionnaire.question3,
            'academic_performance': questionnaire.question4,
            'learning_goals': questionnaire.question5,
            'interests': questionnaire.question6.split(',')
        }
    }
    
    return jsonify(profile), 200
