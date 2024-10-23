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
    # Get nouns and important words
    tagged = nltk.pos_tag(tokens)
    topics = [word for word, tag in tagged 
             if word not in stop_words 
             and len(word) > 3 
             and tag in ['NN', 'NNS', 'NNP', 'NNPS']]
    return list(set(topics))

def find_similar_questions(current_question, user_id, limit=5):
    """Find similar previous questions using TF-IDF and cosine similarity"""
    # Get user's chat history
    history = ChatHistory.query.filter_by(
        user_id=user_id,
        helpful=True  # Only consider helpful interactions
    ).order_by(ChatHistory.timestamp.desc()).all()
    
    if not history:
        return []
    
    # Prepare texts for comparison
    previous_questions = [chat.message for chat in history]
    
    if not previous_questions:
        return []
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english')
    all_questions = [current_question] + previous_questions
    tfidf_matrix = vectorizer.fit_transform(all_questions)
    
    # Calculate similarities
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
    
    # Get most similar questions with their responses
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
            'interaction_pattern': 'new',
            'learning_style': 'balanced',
            'topic_clusters': {}
        }

    # Calculate basic metrics
    avg_complexity = sum(chat.complexity_level or 1 for chat in recent_chats) / len(recent_chats)
    avg_understanding = sum(chat.user_understanding or 3 for chat in recent_chats) / len(recent_chats)
    
    # Analyze topics and create clusters
    topic_clusters = {}
    all_topics = []
    for chat in recent_chats:
        topics = extract_topics(chat.message)
        all_topics.extend(topics)
        for topic in topics:
            if topic not in topic_clusters:
                topic_clusters[topic] = {
                    'count': 0,
                    'avg_understanding': 0,
                    'helpful_count': 0
                }
            topic_clusters[topic]['count'] += 1
            topic_clusters[topic]['avg_understanding'] += chat.user_understanding or 3
            if chat.helpful:
                topic_clusters[topic]['helpful_count'] += 1

    # Calculate topic statistics
    for topic in topic_clusters:
        cluster = topic_clusters[topic]
        cluster['avg_understanding'] /= cluster['count']
        cluster['success_rate'] = cluster['helpful_count'] / cluster['count']

    # Determine preferred topics
    preferred_topics = sorted(
        topic_clusters.items(),
        key=lambda x: (x[1]['count'], x[1]['success_rate']),
        reverse=True
    )[:5]

    # Analyze learning patterns
    helpful_ratio = sum(1 for chat in recent_chats if chat.helpful) / len(recent_chats)
    understanding_trend = [chat.user_understanding or 3 for chat in recent_chats]
    learning_style = 'advancing' if np.mean(understanding_trend[:5]) > np.mean(understanding_trend[-5:]) else 'stable'
    
    return {
        'avg_complexity': avg_complexity,
        'understanding_level': avg_understanding,
        'preferred_topics': [topic for topic, _ in preferred_topics],
        'interaction_pattern': 'advancing' if helpful_ratio > 0.7 else 'struggling',
        'learning_style': learning_style,
        'topic_clusters': topic_clusters
    }

def get_tailored_prompt(user_type, message, user_progress, similar_interactions):
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
        
        # Estimate complexity based on user progress
        base_complexity = min(max(1, int(current_user.interaction_count / 10) + 1), 5)
        topic_complexity = 0
        
        # Adjust complexity based on topic performance
        if main_topic in user_progress['topic_clusters']:
            topic_stats = user_progress['topic_clusters'][main_topic]
            topic_complexity = int(topic_stats['avg_understanding'])
        
        final_complexity = min(5, max(1, (base_complexity + topic_complexity) // 2))
        
        # Save the chat history with enhanced tracking
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message,
            response=ai_response,
            complexity_level=final_complexity,
            user_understanding=None,  # Will be updated with feedback
            topic=main_topic
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({
            'response': ai_response,
            'chat_id': chat_entry.id,
            'complexity_level': final_complexity
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        'understanding': chat.user_understanding,
        'topic': chat.topic
    } for chat in history]
    
    return jsonify(chat_history), 200
