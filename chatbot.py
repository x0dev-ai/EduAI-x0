import os
import nltk
from flask import Blueprint, request, jsonify
from models import User, ChatHistory, db
from auth import token_required
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from datetime import datetime
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import numpy as np
from textblob import TextBlob

# Create blueprint
chatbot_bp = Blueprint('chatbot', __name__)

# Initialize MistralAI client
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

def analyze_sentiment(text):
    """Analyze sentiment of user messages"""
    blob = TextBlob(text)
    return blob.sentiment.polarity

def extract_concepts(text):
    """Extract key concepts from the text"""
    try:
        tokens = word_tokenize(text.lower())
        stop_words = set(stopwords.words('spanish') + stopwords.words('english'))
        tagged = nltk.pos_tag(tokens)
        concepts = [word for word, tag in tagged 
                   if word not in stop_words 
                   and len(word) > 3 
                   and tag in ['NN', 'NNS', 'NNP', 'NNPS']]
        return list(set(concepts))
    except Exception as e:
        print(f"Error extracting concepts: {e}")
        return []

def calculate_engagement_score(chat_history):
    """Calculate user engagement based on interaction patterns"""
    if not chat_history:
        return 0.5
    
    factors = {
        'response_time': [],
        'message_length': [],
        'feedback_score': [],
        'understanding_level': []
    }
    
    for chat in chat_history:
        if chat.response_time:
            factors['response_time'].append(min(chat.response_time / 300, 1))
        factors['message_length'].append(min(len(chat.message) / 500, 1))
        if chat.helpful is not None:
            factors['feedback_score'].append(1.0 if chat.helpful else 0.0)
        if chat.user_understanding:
            factors['understanding_level'].append(chat.user_understanding / 5)
    
    scores = []
    weights = {'response_time': 0.2, 'message_length': 0.3, 
               'feedback_score': 0.25, 'understanding_level': 0.25}
    
    for factor, values in factors.items():
        if values:
            scores.append(np.mean(values) * weights[factor])
    
    return np.sum(scores) if scores else 0.5

def get_tailored_prompt(user_type, message, user_progress, similar_interactions):
    base_system_prompt = '''
    Eres un tutor de IA especializado en educación. Debes responder en español y adaptar tu estilo según el tipo de estudiante.
    '''
    
    # Add learning difficulty adaptations
    if user_progress.get('learning_difficulty') == 'TDAH':
        base_system_prompt += '''
        Adaptaciones para TDAH:
        - Divide la información en segmentos cortos y manejables
        - Usa viñetas y listas para organizar la información
        - Destaca los puntos clave
        - Mantén un tono motivador y energético
        '''
    elif user_progress.get('learning_difficulty') == 'Dislexia':
        base_system_prompt += '''
        Adaptaciones para Dislexia:
        - Usa un lenguaje claro y directo
        - Evita párrafos largos
        - Estructura la información de forma jerárquica
        - Refuerza conceptos clave con ejemplos
        '''
    
    # Add analytics information
    analytics = f"""
    Análisis del progreso del estudiante:
    - Nivel de complejidad actual: {user_progress.get('complexity_level', 3)}/5
    - Nivel de comprensión: {user_progress.get('understanding_level', 3)}/5
    - Patrón de aprendizaje: {user_progress.get('learning_pattern', 'equilibrado')}
    - Engagement: {user_progress.get('engagement_score', 0.5):.2f}
    """
    
    # Add context from similar interactions
    context = "\nContexto de interacciones anteriores relevantes:\n"
    for idx, interaction in enumerate(similar_interactions, 1):
        context += f"{idx}. Pregunta similar: {interaction['question']}\n"
        context += f"   Respuesta exitosa: {interaction['response']}\n"
        context += f"   Nivel de comprensión: {interaction.get('understanding', 3)}/5\n"
    
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
    start_time = time.time()
    message = request.form.get('message', '')
    
    if not message:
        return jsonify({'error': 'No se proporcionó ningún mensaje'}), 400
    
    # Get user's recent chat history
    recent_chats = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(10).all()
    
    # Calculate engagement score
    engagement_score = calculate_engagement_score(recent_chats)
    
    # Analyze sentiment
    sentiment_score = analyze_sentiment(message)
    
    # Extract concepts
    concepts = extract_concepts(message)
    
    # Calculate current complexity level based on user's performance
    avg_understanding = np.mean([chat.user_understanding for chat in recent_chats if chat.user_understanding]) \
        if recent_chats else 3
    
    complexity_level = min(5, max(1, int(avg_understanding + 0.5)))
    
    # Prepare user progress data
    user_progress = {
        'complexity_level': complexity_level,
        'understanding_level': avg_understanding,
        'engagement_score': engagement_score,
        'sentiment_score': sentiment_score,
        'learning_pattern': 'advancing' if engagement_score > 0.7 else 'stable',
        'learning_difficulty': recent_chats[0].learning_difficulty if recent_chats else None
    }
    
    # Find similar previous interactions
    similar_interactions = []
    if recent_chats:
        vectorizer = TfidfVectorizer(stop_words='english')
        messages = [chat.message for chat in recent_chats]
        tfidf_matrix = vectorizer.fit_transform([message] + messages)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        
        for idx in (-similarities).argsort()[:3]:
            if similarities[idx] > 0.3:
                similar_interactions.append({
                    'question': recent_chats[idx].message,
                    'response': recent_chats[idx].response,
                    'understanding': recent_chats[idx].user_understanding
                })

    try:
        # Get tailored prompt
        messages = get_tailored_prompt(current_user.user_type, message, user_progress, similar_interactions)
        
        # Get AI response
        chat_response = mistral_client.chat(
            model="mistral-tiny",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        ai_response = chat_response.choices[0].message.content
        response_time = time.time() - start_time
        
        # Save chat history with incremental learning metrics
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message,
            response=ai_response,
            complexity_level=complexity_level,
            response_time=response_time,
            sentiment_score=sentiment_score,
            engagement_score=engagement_score,
            concepts_covered=concepts
        )
        
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({
            'response': ai_response,
            'chat_id': chat_entry.id,
            'complexity_level': complexity_level
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chat_feedback', methods=['POST'])
@token_required
def chat_feedback(current_user):
    data = request.json
    chat_id = data.get('chat_id')
    helpful = data.get('helpful')
    understanding = data.get('understanding')
    
    if not chat_id:
        return jsonify({'error': 'Chat ID is required'}), 400
    
    try:
        chat = ChatHistory.query.filter_by(id=chat_id, user_id=current_user.id).first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Update chat history with feedback
        chat.helpful = helpful if helpful is not None else chat.helpful
        chat.user_understanding = understanding if understanding else chat.user_understanding
        
        # Calculate interaction quality
        if helpful is not None and understanding:
            chat.interaction_quality = (helpful + (understanding / 5)) / 2
        
        # Calculate learning progress
        if chat.user_understanding and len(recent_chats) > 1:
            prev_understanding = np.mean([c.user_understanding for c in recent_chats[1:] if c.user_understanding])
            chat.learning_progress = (chat.user_understanding / 5) - (prev_understanding / 5)
        
        db.session.commit()
        return jsonify({'message': 'Feedback submitted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
