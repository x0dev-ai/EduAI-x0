import os
import re
from flask import Blueprint, request, jsonify
from models import User, ChatHistory, db
from auth import token_required
from openai import OpenAI

chatbot_bp = Blueprint('chatbot', __name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def preprocess_text(text):
    """
    Preprocess input text according to specifications:
    - Remove duplicates
    - Fix typos (basic)
    - Handle missing values
    - Normalize text
    """
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    # Convert to lowercase
    text = text.lower()
    # Basic typo correction for common Spanish words
    common_typos = {
        'q ': 'que ',
        'xq': 'porque',
        'k ': 'que ',
        'tb ': 'también ',
    }
    for typo, correction in common_typos.items():
        text = text.replace(typo, correction)
    # Remove duplicate words
    words = text.split()
    text = ' '.join(dict.fromkeys(words))
    return text

def get_tailored_prompt(user_type, message):
    """Generate tailored prompts based on user type with specific Spanish instructions"""
    base_system_prompt = """
    Eres un tutor de IA especializado en educación. Debes responder en español y adaptar tu estilo según el tipo de estudiante.
    """
    
    if user_type == 'A':
        system_prompt = base_system_prompt + """
        Para estudiantes tipo A (alto rendimiento):
        - Proporciona explicaciones detalladas y profundas
        - Incluye referencias académicas cuando sea relevante
        - Plantea preguntas desafiantes para estimular el pensamiento crítico
        - Sugiere recursos adicionales avanzados
        """
    elif user_type == 'B':
        system_prompt = base_system_prompt + """
        Para estudiantes tipo B (rendimiento medio):
        - Ofrece explicaciones balanceadas y claras
        - Incluye ejemplos prácticos
        - Proporciona pasos intermedios en las explicaciones
        - Sugiere ejercicios de práctica moderados
        """
    else:  # type C
        system_prompt = base_system_prompt + """
        Para estudiantes tipo C (necesita apoyo adicional):
        - Da explicaciones simples y directas
        - Usa muchos ejemplos de la vida cotidiana
        - Divide la información en pasos pequeños y manejables
        - Ofrece refuerzo positivo constante
        """
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Responde a la siguiente consulta: {message}"}
    ]

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    message = request.json.get('message')
    if not message:
        return jsonify({'error': 'No se proporcionó ningún mensaje'}), 400

    # Preprocess the input message
    processed_message = preprocess_text(message)
    
    # Get user type and create tailored messages
    user_type = current_user.user_type
    messages = get_tailored_prompt(user_type, processed_message)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        ai_response = response.choices[0].message.content

        # Save the chat history
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message,
            response=ai_response
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({'response': ai_response}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chat_history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).limit(10).all()
    chat_history = [{'message': chat.message, 'response': chat.response, 'timestamp': chat.timestamp} for chat in history]
    return jsonify(chat_history), 200
