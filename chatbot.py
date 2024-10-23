import os
from flask import Blueprint, request, jsonify
from models import User, ChatHistory, db
from auth import token_required
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from datetime import datetime, timedelta
import json

chatbot_bp = Blueprint('chatbot', __name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

def analyze_user_progress(user_id):
    """Analyze user's learning progress based on chat history"""
    recent_chats = ChatHistory.query.filter_by(user_id=user_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(10).all()
    
    if not recent_chats:
        return {
            'avg_complexity': 1,
            'understanding_level': 3,
            'preferred_topics': [],
            'interaction_pattern': 'new'
        }

    # Calculate metrics
    avg_complexity = sum(chat.complexity_level or 1 for chat in recent_chats) / len(recent_chats)
    avg_understanding = sum(chat.user_understanding or 3 for chat in recent_chats) / len(recent_chats)
    
    # Analyze topics
    topics = [chat.topic for chat in recent_chats if chat.topic]
    topic_frequency = {}
    for topic in topics:
        topic_frequency[topic] = topic_frequency.get(topic, 0) + 1
    
    preferred_topics = sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Determine interaction pattern
    total_helpful = sum(1 for chat in recent_chats if chat.helpful)
    interaction_pattern = 'advancing' if total_helpful/len(recent_chats) > 0.7 else 'struggling'
    
    return {
        'avg_complexity': avg_complexity,
        'understanding_level': avg_understanding,
        'preferred_topics': [topic for topic, _ in preferred_topics],
        'interaction_pattern': interaction_pattern
    }

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

def get_tailored_prompt(user_type, message, user_progress):
    base_system_prompt = '''
    Eres un tutor de IA especializado en educación. Debes responder en español y adaptar tu estilo según el tipo de estudiante.
    '''
    
    # Adjust complexity based on user progress
    complexity_adjustment = f'''
    - Nivel de complejidad sugerido: {user_progress['avg_complexity']}/5
    - Nivel de comprensión del usuario: {user_progress['understanding_level']}/5
    - Patrón de interacción: {user_progress['interaction_pattern']}
    '''
    
    if user_type == 'ESTRUCTURADO':
        system_prompt = base_system_prompt + f'''
        Para estudiantes estructurados:
        - Proporciona explicaciones detalladas y analíticas
        - Incluye referencias académicas cuando sea relevante
        - Plantea preguntas desafiantes para estimular el pensamiento crítico
        - Sugiere recursos adicionales avanzados
        {complexity_adjustment}
        '''
    elif user_type == 'EXPLORADOR':
        system_prompt = base_system_prompt + f'''
        Para estudiantes exploradores:
        - Ofrece explicaciones balanceadas y claras
        - Incluye ejemplos prácticos
        - Proporciona pasos intermedios en las explicaciones
        - Sugiere ejercicios de práctica moderados
        {complexity_adjustment}
        '''
    else:  # INTENSIVO
        system_prompt = base_system_prompt + f'''
        Para estudiantes intensivos:
        - Da explicaciones simples y directas
        - Usa muchos ejemplos de la vida cotidiana
        - Divide la información en pasos pequeños y manejables
        - Ofrece refuerzo positivo constante
        {complexity_adjustment}
        '''
    
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Responde a la siguiente consulta: {message}")
    ]

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    message = request.json.get('message')
    if not message:
        return jsonify({'error': 'No se proporcionó ningún mensaje'}), 400

    # Preprocess the input message
    processed_message = preprocess_text(message)
    
    # Get user progress and analytics
    user_progress = analyze_user_progress(current_user.id)
    
    # Get user type and create tailored messages
    user_type = current_user.user_type
    messages = get_tailored_prompt(user_type, processed_message, user_progress)

    try:
        chat_response = mistral_client.chat(
            model="mistral-tiny",  # Using tiny model for faster responses
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        ai_response = chat_response.choices[0].message.content

        # Update user interaction count
        current_user.interaction_count += 1
        
        # Estimate initial complexity and understanding levels
        estimated_complexity = min(
            max(1, int(current_user.interaction_count / 10) + 1), 
            5
        )
        
        # Save the chat history with enhanced tracking
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message,
            response=ai_response,
            complexity_level=estimated_complexity,
            user_understanding=3,  # Default middle value until feedback
            topic="general"  # This could be enhanced with topic detection
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({
            'response': ai_response,
            'chat_id': chat_entry.id,
            'complexity_level': estimated_complexity
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chat_feedback', methods=['POST'])
@token_required
def submit_feedback(current_user):
    data = request.json
    chat_id = data.get('chat_id')
    helpful = data.get('helpful')
    understanding = data.get('understanding')
    
    if not chat_id:
        return jsonify({'error': 'Chat ID is required'}), 400
        
    try:
        chat = ChatHistory.query.filter_by(
            id=chat_id, 
            user_id=current_user.id
        ).first()
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
            
        chat.helpful = helpful
        if understanding:
            chat.user_understanding = understanding
            
        db.session.commit()
        return jsonify({'message': 'Feedback submitted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chat_history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(10).all()
    
    chat_history = [{
        'id': chat.id,
        'message': chat.message,
        'response': chat.response,
        'timestamp': chat.timestamp,
        'complexity_level': chat.complexity_level,
        'helpful': chat.helpful,
        'understanding': chat.user_understanding
    } for chat in history]
    
    return jsonify(chat_history), 200
