import os
from flask import Blueprint, request, jsonify
from models import User, ChatHistory, db
from auth import token_required
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from datetime import datetime, timedelta
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import numpy as np
import time

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')

chatbot_bp = Blueprint('chatbot', __name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

def extract_topics(text):
    """Extract main topics from text using NLTK"""
    tokens = word_tokenize(text.lower())
    stop_words = set(stopwords.words('spanish') + stopwords.words('english'))
    tagged = nltk.pos_tag(tokens)
    topics = [word for word, tag in tagged 
             if word not in stop_words 
             and len(word) > 3 
             and tag in ['NN', 'NNS', 'NNP', 'NNPS']]
    return list(set(topics))

def find_similar_questions(current_question, user_id, limit=5):
    """Find similar previous questions using TF-IDF and cosine similarity"""
    history = ChatHistory.query.filter_by(
        user_id=user_id,
        helpful=True  # Only consider helpful interactions
    ).order_by(ChatHistory.timestamp.desc()).all()
    
    if not history:
        return []
    
    previous_questions = [chat.message for chat in history]
    
    if not previous_questions:
        return []
    
    vectorizer = TfidfVectorizer(stop_words='english')
    all_questions = [current_question] + previous_questions
    tfidf_matrix = vectorizer.fit_transform(all_questions)
    
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
    
    similar_interactions = []
    for idx in (-similarities).argsort()[:limit]:
        if similarities[idx] > 0.3:  # Similarity threshold
            similar_interactions.append({
                'question': history[idx].message,
                'response': history[idx].response,
                'similarity': similarities[idx]
            })
    
    return similar_interactions

def analyze_user_progress(user_id):
    """Enhanced analysis of user's learning progress"""
    recent_chats = ChatHistory.query.filter_by(user_id=user_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(20).all()
    
    if not recent_chats:
        return {
            'avg_complexity': 1,
            'understanding_level': 3,
            'preferred_topics': [],
            'learning_style': 'balanced',
            'learning_pace': 'normal'
        }

    # Calculate basic metrics
    avg_complexity = sum(chat.complexity_level or 1 for chat in recent_chats) / len(recent_chats)
    avg_understanding = sum(chat.user_understanding or 3 for chat in recent_chats) / len(recent_chats)
    
    # Analyze learning pace
    timestamps = [chat.timestamp for chat in recent_chats]
    if len(timestamps) > 1:
        time_diffs = [(t2 - t1).total_seconds() / 3600 
                     for t1, t2 in zip(timestamps[1:], timestamps[:-1])]
        avg_time_between = np.mean(time_diffs)
        learning_pace = (
            'intensive' if avg_time_between < 24 else
            'regular' if avg_time_between < 72 else
            'casual'
        )
    else:
        learning_pace = 'normal'

    # Calculate comprehension trends
    understanding_sequence = [chat.user_understanding or 3 for chat in recent_chats]
    if len(understanding_sequence) > 5:
        trend_slope = np.polyfit(range(len(understanding_sequence)), 
                               understanding_sequence, 1)[0]
        learning_style = (
            'advancing' if trend_slope > 0.1 else
            'stable' if abs(trend_slope) <= 0.1 else
            'struggling'
        )
    else:
        learning_style = 'balanced'

    # Get preferred topics
    topics = []
    for chat in recent_chats:
        if chat.helpful:
            topics.extend(extract_topics(chat.message))
    
    preferred_topics = [topic for topic, count 
                       in sorted([(t, topics.count(t)) for t in set(topics)], 
                               key=lambda x: x[1], 
                               reverse=True)[:5]]

    return {
        'avg_complexity': avg_complexity,
        'understanding_level': avg_understanding,
        'preferred_topics': preferred_topics,
        'learning_style': learning_style,
        'learning_pace': learning_pace
    }

def get_tailored_prompt(user_type, message, user_progress, similar_interactions):
    """Generate a tailored prompt based on user type and learning progress"""
    base_system_prompt = '''
    Eres un tutor de IA especializado en educación. Debes responder en español y adaptar tu estilo según el tipo de estudiante.
    '''
    
    # Add context from similar interactions
    context = "\nContexto de interacciones anteriores relevantes:\n"
    for idx, interaction in enumerate(similar_interactions, 1):
        context += f"{idx}. Pregunta similar: {interaction['question']}\n"
        context += f"   Respuesta exitosa: {interaction['response']}\n"
    
    # Add learning analytics
    analytics = f"""
    Análisis del progreso del estudiante:
    - Nivel de complejidad actual: {user_progress['avg_complexity']}/5
    - Nivel de comprensión: {user_progress['understanding_level']}/5
    - Patrón de aprendizaje: {user_progress['learning_style']}
    - Temas preferidos: {', '.join(user_progress['preferred_topics'])}
    """
    
    if user_type == 'ESTRUCTURADO':
        system_prompt = base_system_prompt + f'''
        Para estudiantes estructurados:
        - Proporciona explicaciones detalladas y analíticas
        - Incluye referencias académicas cuando sea relevante
        - Plantea preguntas desafiantes para estimular el pensamiento crítico
        - Sugiere recursos adicionales avanzados
        {analytics}
        {context}
        '''
    elif user_type == 'EXPLORADOR':
        system_prompt = base_system_prompt + f'''
        Para estudiantes exploradores:
        - Ofrece explicaciones balanceadas y claras
        - Incluye ejemplos prácticos
        - Proporciona pasos intermedios en las explicaciones
        - Sugiere ejercicios de práctica moderados
        {analytics}
        {context}
        '''
    else:  # INTENSIVO
        system_prompt = base_system_prompt + f'''
        Para estudiantes intensivos:
        - Da explicaciones simples y directas
        - Usa muchos ejemplos de la vida cotidiana
        - Divide la información en pasos pequeños y manejables
        - Ofrece refuerzo positivo constante
        {analytics}
        {context}
        '''
    
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Responde a la siguiente consulta: {message}")
    ]

def preprocess_text(text):
    """Preprocess input text"""
    text = ' '.join(text.split())
    text = text.lower()
    common_typos = {
        'q ': 'que ',
        'xq': 'porque',
        'k ': 'que ',
        'tb ': 'también ',
    }
    for typo, correction in common_typos.items():
        text = text.replace(typo, correction)
    words = text.split()
    text = ' '.join(dict.fromkeys(words))
    return text

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    start_time = time.time()
    message = request.json.get('message')
    if not message:
        return jsonify({'error': 'No se proporcionó ningún mensaje'}), 400

    # Preprocess the input message
    processed_message = preprocess_text(message)
    
    # Get user progress and analytics
    user_progress = analyze_user_progress(current_user.id)
    
    # Find similar previous interactions
    similar_interactions = find_similar_questions(processed_message, current_user.id)
    
    # Get user type and create tailored messages
    user_type = current_user.user_type
    messages = get_tailored_prompt(user_type, processed_message, user_progress, similar_interactions)

    try:
        chat_response = mistral_client.chat(
            model="mistral-tiny",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        ai_response = chat_response.choices[0].message.content

        # Extract topics from the conversation
        topics = extract_topics(processed_message)
        main_topic = topics[0] if topics else "general"
        
        # Update user interaction count
        current_user.interaction_count += 1
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Save the chat history with enhanced tracking
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message,
            response=ai_response,
            complexity_level=user_progress['avg_complexity'],
            user_understanding=None,  # Will be updated with feedback
            topic=main_topic,
            response_time=response_time,
            session_duration=None,  # Will be updated with feedback
            preferred_pace=user_progress['learning_pace'],
            interaction_quality=None  # Will be calculated after feedback
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({
            'response': ai_response,
            'chat_id': chat_entry.id,
            'complexity_level': user_progress['avg_complexity']
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
            
        # Calculate interaction quality
        if helpful is not None and understanding:
            chat.interaction_quality = (helpful + (understanding / 5)) / 2
            
        # Update session duration
        if chat.timestamp:
            session_duration = (datetime.utcnow() - chat.timestamp).total_seconds()
            chat.session_duration = int(session_duration)
            
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
        'understanding': chat.user_understanding,
        'topic': chat.topic
    } for chat in history]
    
    return jsonify(chat_history), 200

@chatbot_bp.route('/learning_report', methods=['GET'])
@token_required
def get_learning_report(current_user):
    user_progress = analyze_user_progress(current_user.id)
    if not user_progress:
        return jsonify({'error': 'Could not generate learning report'}), 404
    return jsonify(user_progress), 200
