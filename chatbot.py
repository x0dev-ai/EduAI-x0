import os
from flask import Blueprint, request, jsonify
from models import User, ChatHistory, db
from auth import token_required
from openai import OpenAI

chatbot_bp = Blueprint('chatbot', __name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    message = request.json.get('message')
    if not message:
        return jsonify({'error': 'No message provided'}), 400

    # Get user type and tailor the response accordingly
    user_type = current_user.user_type
    tailored_prompt = get_tailored_prompt(user_type, message)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": tailored_prompt}]
        )
        ai_response = response.choices[0].message.content

        # Save the chat history
        chat_entry = ChatHistory(user_id=current_user.id, message=message, response=ai_response)
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({'response': ai_response}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_tailored_prompt(user_type, message):
    base_prompt = f"As an AI tutor for a {user_type} type student, respond to the following: {message}"
    
    if user_type == 'A':
        return base_prompt + " Provide a detailed and challenging response."
    elif user_type == 'B':
        return base_prompt + " Offer a balanced explanation with some additional insights."
    else:  # type C
        return base_prompt + " Give a clear and simple explanation with examples."

@chatbot_bp.route('/chat_history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    chat_history = [{'message': chat.message, 'response': chat.response, 'timestamp': chat.timestamp} for chat in history]
    return jsonify(chat_history), 200
