import os
import nltk
from flask import Blueprint, request, jsonify
from models import User, ChatHistory, QuestionnaireResponse, db
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
import time
from werkzeug.utils import secure_filename

nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
os.makedirs(nltk_data_dir, exist_ok=True)

nltk.data.path.append(nltk_data_dir)

def download_nltk_data():
    try:
        nltk.download('punkt', download_dir=nltk_data_dir, quiet=True)
        nltk.download('stopwords', download_dir=nltk_data_dir, quiet=True)
        nltk.download('averaged_perceptron_tagger', download_dir=nltk_data_dir, quiet=True)
    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
        return False
    return True

if not download_nltk_data():
    print("Warning: NLTK data download failed, some features may not work properly")

chatbot_bp = Blueprint('chatbot', __name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

def extract_topics(text):
    try:
        tokens = word_tokenize(text.lower())
        stop_words = set(stopwords.words('spanish') + stopwords.words('english'))
        tagged = nltk.pos_tag(tokens)
        topics = [word for word, tag in tagged 
                if word not in stop_words 
                and len(word) > 3 
                and tag in ['NN', 'NNS', 'NNP', 'NNPS']]
        return list(set(topics))
    except Exception as e:
        print(f"Error in topic extraction: {e}")
        return [text.lower()]

def find_similar_questions(current_question, user_id, limit=5):
    history = ChatHistory.query.filter_by(
        user_id=user_id,
        helpful=True
    ).order_by(ChatHistory.timestamp.desc()).all()
    
    if not history:
        return []
    
    previous_questions = [chat.message for chat in history]
    
    if not previous_questions:
        return []
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        all_questions = [current_question] + previous_questions
        tfidf_matrix = vectorizer.fit_transform(all_questions)
        
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        
        similar_interactions = []
        for idx in (-similarities).argsort()[:limit]:
            if similarities[idx] > 0.3:
                similar_interactions.append({
                    'question': history[idx].message,
                    'response': history[idx].response,
                    'similarity': similarities[idx],
                    'understanding': history[idx].user_understanding
                })
        
        return similar_interactions
    except Exception as e:
        print(f"Error finding similar questions: {e}")
        return []

def analyze_user_progress(user_id):
    recent_chats = ChatHistory.query.filter_by(user_id=user_id)\
        .order_by(ChatHistory.timestamp.desc())\
        .limit(20).all()
    
    if not recent_chats:
        return {
            'avg_complexity': 1,
            'understanding_level': 3,
            'preferred_topics': [],
            'learning_style': 'balanced',
            'learning_pace': 'normal',
            'mastery_scores': {},
            'user_id': user_id
        }

    avg_complexity = sum(chat.complexity_level or 1 for chat in recent_chats) / len(recent_chats)
    avg_understanding = sum(chat.user_understanding or 3 for chat in recent_chats) / len(recent_chats)
    
    topic_interactions = {}
    for chat in recent_chats:
        if chat.topic not in topic_interactions:
            topic_interactions[chat.topic] = []
        topic_interactions[chat.topic].append({
            'understanding': chat.user_understanding or 3,
            'helpful': chat.helpful,
            'timestamp': chat.timestamp
        })
    
    mastery_scores = {}
    for topic, interactions in topic_interactions.items():
        total_weight = 0
        weighted_score = 0
        for idx, interaction in enumerate(interactions):
            weight = 1 / (idx + 1)
            score = (interaction['understanding'] / 5.0) * (1.5 if interaction['helpful'] else 0.5)
            weighted_score += score * weight
            total_weight += weight
        mastery_scores[topic] = weighted_score / total_weight if total_weight > 0 else 0

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

    if len(recent_chats) > 5:
        understanding_trend = np.polyfit(range(len(recent_chats)),
                                       [chat.user_understanding or 3 for chat in recent_chats],
                                       1)[0]
        learning_style = (
            'advancing' if understanding_trend > 0.1 else
            'stable' if abs(understanding_trend) <= 0.1 else
            'struggling'
        )
    else:
        learning_style = 'balanced'

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
        'learning_pace': learning_pace,
        'mastery_scores': mastery_scores,
        'user_id': user_id
    }

def preprocess_text(text):
    if not text:
        return ""
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
    return text

def get_tailored_prompt(user_type, message, user_progress, similar_interactions):
    base_system_prompt = '''
    Eres un tutor de IA especializado en educación. Debes responder en español y adaptar tu estilo según el tipo de estudiante.
    '''
    
    user = User.query.get(user_progress.get('user_id'))
    if user:
        questionnaire = QuestionnaireResponse.query.filter_by(user_id=user.id).first()
        if questionnaire and questionnaire.learning_difficulty:
            if questionnaire.learning_difficulty == 'TDAH':
                base_system_prompt += '''
                Para estudiantes con TDAH:
                - Divide la información en bloques cortos y manejables
                - Usa elementos visuales y ejemplos concretos
                - Mantén un ritmo dinámico pero estructurado
                - Proporciona recordatorios y refuerzos frecuentes
                '''
            elif questionnaire.learning_difficulty == 'Dislexia':
                base_system_prompt += '''
                Para estudiantes con Dislexia:
                - Usa un lenguaje claro y directo
                - Evita textos largos y complejos
                - Proporciona alternativas audiovisuales cuando sea posible
                - Da tiempo extra para procesar la información
                '''
    
    if user_type == 'ESTRUCTURADO':
        base_system_prompt += '''
        Para estudiantes estructurados:
        - Proporciona explicaciones detalladas y analíticas
        - Incluye referencias académicas cuando sea relevante
        - Plantea preguntas desafiantes para estimular el pensamiento crítico
        - Sugiere recursos adicionales avanzados
        '''
    elif user_type == 'EXPLORADOR':
        base_system_prompt += '''
        Para estudiantes exploradores:
        - Ofrece explicaciones balanceadas y claras
        - Incluye ejemplos prácticos
        - Proporciona pasos intermedios en las explicaciones
        - Sugiere ejercicios de práctica moderados
        '''
    else:  # INTENSIVO
        base_system_prompt += '''
        Para estudiantes intensivos:
        - Da explicaciones simples y directas
        - Usa muchos ejemplos de la vida cotidiana
        - Divide la información en pasos pequeños y manejables
        - Ofrece refuerzo positivo constante
        '''
    
    return [
        ChatMessage(role="system", content=base_system_prompt),
        ChatMessage(role="user", content=f"Responde a la siguiente consulta: {message}")
    ]

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    start_time = time.time()
    message = request.form.get('message', '')
    file = request.files.get('file')
    
    if not message and not file:
        return jsonify({'error': 'No se proporcionó ningún mensaje o archivo'}), 400
        
    file_info = ""
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_info = f"\nArchivo adjunto: {filename}"
        
    processed_message = preprocess_text(message + file_info if file_info else message)
    
    user_progress = analyze_user_progress(current_user.id)
    
    similar_interactions = find_similar_questions(processed_message, current_user.id)
    
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

        topics = extract_topics(processed_message)
        main_topic = topics[0] if topics else "general"
        
        current_user.interaction_count += 1
        
        response_time = time.time() - start_time
        
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message + file_info if file_info else message,
            response=ai_response,
            complexity_level=user_progress['avg_complexity'],
            topic=main_topic,
            response_time=response_time,
            preferred_pace=user_progress['learning_pace']
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
            
        chat.helpful = helpful if helpful is not None else chat.helpful
        if understanding:
            chat.user_understanding = understanding
            
        if helpful is not None and understanding:
            chat.interaction_quality = (helpful + (understanding / 5)) / 2
            
        if chat.timestamp:
            session_duration = (datetime.utcnow() - chat.timestamp).total_seconds()
            chat.session_duration = int(session_duration)
            
        db.session.commit()
        return jsonify({'message': 'Feedback submitted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/learning_report', methods=['GET'])
@token_required
def get_learning_report(current_user):
    user_progress = analyze_user_progress(current_user.id)
    if not user_progress:
        return jsonify({'error': 'Could not generate learning report'}), 404
    return jsonify(user_progress), 200