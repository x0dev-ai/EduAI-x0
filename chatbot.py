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
    # Get nouns and important words
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

def calculate_success_metrics(user_id):
    """Calculate success metrics for a user's learning journey"""
    recent_chats = ChatHistory.query.filter_by(user_id=user_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(50).all()
    
    if not recent_chats:
        return {
            'overall_success_rate': 0,
            'avg_response_time': 0,
            'comprehension_trend': 'new',
            'mastery_levels': {},
            'engagement_score': 0
        }
    
    # Calculate metrics
    success_rate = sum(1 for chat in recent_chats if chat.helpful) / len(recent_chats)
    avg_response_time = sum(chat.response_time or 0 for chat in recent_chats) / len(recent_chats)
    
    # Analyze comprehension trend
    understanding_scores = [chat.user_understanding for chat in recent_chats if chat.user_understanding]
    if understanding_scores:
        recent_avg = np.mean(understanding_scores[:10])
        older_avg = np.mean(understanding_scores[-10:]) if len(understanding_scores) > 10 else recent_avg
        comprehension_trend = 'improving' if recent_avg > older_avg else 'stable' if recent_avg == older_avg else 'declining'
    else:
        comprehension_trend = 'insufficient_data'
    
    # Calculate topic mastery levels
    topic_interactions = {}
    for chat in recent_chats:
        if chat.topic not in topic_interactions:
            topic_interactions[chat.topic] = {
                'total': 0,
                'successful': 0,
                'understanding': []
            }
        topic_interactions[chat.topic]['total'] += 1
        if chat.helpful:
            topic_interactions[chat.topic]['successful'] += 1
        if chat.user_understanding:
            topic_interactions[chat.topic]['understanding'].append(chat.user_understanding)
    
    mastery_levels = {}
    for topic, data in topic_interactions.items():
        success_ratio = data['successful'] / data['total']
        avg_understanding = np.mean(data['understanding']) if data['understanding'] else 3
        mastery_levels[topic] = (success_ratio * 0.6 + (avg_understanding / 5) * 0.4)
    
    # Calculate engagement score based on interaction frequency and quality
    time_weights = np.exp(-np.arange(len(recent_chats)) / 10)  # Exponential decay
    interaction_qualities = [(chat.helpful or 0) * (chat.user_understanding or 3) / 5 for chat in recent_chats]
    engagement_score = np.average(interaction_qualities, weights=time_weights)
    
    return {
        'overall_success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'comprehension_trend': comprehension_trend,
        'mastery_levels': mastery_levels,
        'engagement_score': engagement_score
    }

def generate_learning_report(user_id):
    """Generate a comprehensive learning report"""
    user = User.query.get(user_id)
    if not user:
        return None
    
    metrics = calculate_success_metrics(user_id)
    progress = analyze_user_progress(user_id)
    
    # Get topic recommendations
    low_mastery_topics = [
        topic for topic, mastery in metrics['mastery_levels'].items()
        if mastery < 0.6 and topic != 'general'
    ]
    
    # Analyze learning patterns
    recent_chats = ChatHistory.query.filter_by(user_id=user_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(50).all()
    
    session_durations = [chat.session_duration for chat in recent_chats if chat.session_duration]
    preferred_durations = np.median(session_durations) if session_durations else 0
    
    # Generate report
    report = {
        'user_type': user.user_type,
        'total_interactions': user.interaction_count,
        'success_metrics': metrics,
        'learning_progress': {
            'mastered_topics': [topic for topic, mastery in metrics['mastery_levels'].items() if mastery >= 0.8],
            'topics_needing_review': low_mastery_topics,
            'comprehension_trend': metrics['comprehension_trend'],
            'preferred_learning_duration': preferred_durations
        },
        'recommendations': {
            'suggested_topics': low_mastery_topics[:3],
            'recommended_complexity': min(5, max(1, int(metrics['overall_success_rate'] * 5))),
            'session_duration': f"{int(preferred_durations)} minutes" if preferred_durations else "No data",
            'learning_style_adjustments': []
        }
    }
    
    # Add learning style recommendations
    if metrics['overall_success_rate'] < 0.6:
        report['recommendations']['learning_style_adjustments'].append(
            "Consider simplifying explanations and increasing examples"
        )
    if progress['learning_style'] == 'advancing':
        report['recommendations']['learning_style_adjustments'].append(
            "Ready for more challenging content"
        )
    
    return report

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
            'topic_clusters': {},
            'learning_pace': 'normal',
            'mastery_trends': {}
        }

    # Calculate basic metrics
    avg_complexity = sum(chat.complexity_level or 1 for chat in recent_chats) / len(recent_chats)
    avg_understanding = sum(chat.user_understanding or 3 for chat in recent_chats) / len(recent_chats)
    
    # Enhanced topic analysis with mastery tracking
    topic_clusters = {}
    for chat in recent_chats:
        topics = extract_topics(chat.message)
        for topic in topics:
            if topic not in topic_clusters:
                topic_clusters[topic] = {
                    'count': 0,
                    'avg_understanding': 0,
                    'helpful_count': 0,
                    'complexity_history': [],
                    'understanding_history': [],
                    'mastery_score': 0
                }
            cluster = topic_clusters[topic]
            cluster['count'] += 1
            cluster['avg_understanding'] += chat.user_understanding or 3
            cluster['complexity_history'].append(chat.complexity_level or 1)
            cluster['understanding_history'].append(chat.user_understanding or 3)
            if chat.helpful:
                cluster['helpful_count'] += 1

    # Calculate advanced topic statistics
    for topic, cluster in topic_clusters.items():
        cluster['avg_understanding'] /= cluster['count']
        cluster['success_rate'] = cluster['helpful_count'] / cluster['count']
        
        # Calculate mastery score using complexity and understanding trends
        understanding_trend = np.polyfit(range(len(cluster['understanding_history'])), 
                                       cluster['understanding_history'], 1)[0]
        complexity_trend = np.polyfit(range(len(cluster['complexity_history'])), 
                                    cluster['complexity_history'], 1)[0]
        
        cluster['mastery_score'] = (
            cluster['success_rate'] * 0.4 +
            (cluster['avg_understanding'] / 5) * 0.3 +
            (understanding_trend > 0) * 0.2 +
            (complexity_trend > 0) * 0.1
        )

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
        learning_pace = 'new'

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

    # Determine preferred topics based on enhanced metrics
    preferred_topics = sorted(
        topic_clusters.items(),
        key=lambda x: (x[1]['mastery_score'], x[1]['count']),
        reverse=True
    )[:5]

    return {
        'avg_complexity': avg_complexity,
        'understanding_level': avg_understanding,
        'preferred_topics': [topic for topic, _ in preferred_topics],
        'interaction_pattern': 'advancing' if avg_understanding > 3.5 else 'struggling',
        'learning_style': learning_style,
        'learning_pace': learning_pace,
        'topic_clusters': topic_clusters,
        'mastery_trends': {
            topic: cluster['mastery_score']
            for topic, cluster in topic_clusters.items()
        }
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
    report = generate_learning_report(current_user.id)
    if not report:
        return jsonify({'error': 'Could not generate learning report'}), 404
    return jsonify(report), 200
