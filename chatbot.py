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
        return list(set(topics)) if topics else ["general"]
    except Exception as e:
        print(f"Error in topic extraction: {e}")
        return ["general"]

def calculate_user_progress(user_id):
    chat_history = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).all()
    
    if not chat_history:
        return 0
    
    total_interactions = len(chat_history)
    weighted_progress = 0
    
    for i, chat in enumerate(chat_history):
        weight = 1 / (i + 1)  # Recent interactions have more weight
        interaction_score = 0
        if chat.helpful:
            interaction_score += 0.4
        if chat.user_understanding:
            interaction_score += (chat.user_understanding / 5) * 0.4
        if chat.mastery_level:
            interaction_score += chat.mastery_level * 0.2
            
        weighted_progress += interaction_score * weight
    
    progress = (weighted_progress / (1 if total_interactions == 0 else total_interactions)) * 100
    return min(round(progress), 100)

def get_completed_questions_count(user_id):
    return ChatHistory.query.filter_by(user_id=user_id).count()

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
            weight = 1 / (idx + 1)  # Recent interactions have more weight
            score = (interaction['understanding'] / 5.0) * (1.5 if interaction['helpful'] else 0.5)
            weighted_score += score * weight
            total_weight += weight
        mastery_scores[topic] = weighted_score / total_weight if total_weight > 0 else 0

    # Calculate learning pace based on interaction frequency
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

    # Analyze learning trend
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

    # Extract preferred topics
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

def adapt_response_style(user_type, learning_progress):
    style_adjustments = {
        'ESTRUCTURADO': {
            'struggling': 'Divide la explicación en pasos numerados y usa ejemplos concretos.',
            'stable': 'Mantén una estructura clara y organizada.',
            'advancing': 'Incluye conexiones entre conceptos y profundiza en detalles.'
        },
        'EXPLORADOR': {
            'struggling': 'Usa analogías y ejemplos de la vida real.',
            'stable': 'Combina diferentes perspectivas y enfoques.',
            'advancing': 'Propón retos y preguntas para exploración adicional.'
        },
        'INTENSIVO': {
            'struggling': 'Focaliza en los conceptos esenciales.',
            'stable': 'Mantén un ritmo desafiante pero manejable.',
            'advancing': 'Profundiza en aspectos avanzados y casos especiales.'
        }
    }
    
    learning_state = learning_progress.get('learning_style', 'stable')
    return style_adjustments.get(user_type, {}).get(learning_state, 'Adapta el contenido al nivel del usuario.')

def get_tailored_prompt(user_type, message, user_progress, similar_interactions):
    base_system_prompt = '''
    Eres un tutor de IA especializado en educación. Debes responder en español y adaptar tu estilo según el tipo de estudiante.
    '''
    
    response_style = adapt_response_style(user_type, user_progress)
    base_system_prompt += f"\nEstilo de respuesta: {response_style}\n"
    
    complexity = calculate_response_complexity(user_progress, 
                                            user_progress.get('mastery_scores', {}).get(user_progress.get('preferred_topics', ['general'])[0], 0))
    base_system_prompt += f"\nNivel de complejidad sugerido: {complexity}/5\n"
    
    if similar_interactions:
        base_system_prompt += '''
        Interacciones previas relacionadas:
        '''
        for interaction in similar_interactions:
            base_system_prompt += f"- Pregunta: {interaction['question']}\n"
            base_system_prompt += f"  Comprensión: {interaction['understanding']}/5\n"
    
    mastery_scores = user_progress.get('mastery_scores', {})
    if mastery_scores:
        base_system_prompt += '''
        Niveles de dominio por tema:
        '''
        for topic, score in mastery_scores.items():
            base_system_prompt += f"- {topic}: {score * 100:.0f}%\n"
    
    return [
        ChatMessage(role="system", content=base_system_prompt),
        ChatMessage(role="user", content=f"Responde a la siguiente consulta: {message}")
    ]

def calculate_response_complexity(user_progress, topic_mastery):
    base_complexity = 3
    
    if user_progress.get('learning_style') == 'struggling':
        base_complexity = max(1, base_complexity - 1)
    elif user_progress.get('learning_style') == 'advancing':
        base_complexity = min(5, base_complexity + 1)
    
    if topic_mastery > 0.8:
        base_complexity = min(5, base_complexity + 1)
    elif topic_mastery < 0.4:
        base_complexity = max(1, base_complexity - 1)
        
    return base_complexity

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
    
    # Process message and analyze user progress
    topics = extract_topics(message + file_info if file_info else message)
    main_topic = topics[0] if topics else "general"
    
    user_progress = analyze_user_progress(current_user.id)
    similar_interactions = find_similar_questions(message, current_user.id)
    current_mastery = user_progress['mastery_scores'].get(main_topic, 0)
    
    try:
        messages = get_tailored_prompt(current_user.user_type, 
                                     message,
                                     user_progress,
                                     similar_interactions)
        
        chat_response = mistral_client.chat(
            model="mistral-tiny",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        ai_response = chat_response.choices[0].message.content
        
        # Calculate response complexity and update user progress
        complexity_level = calculate_response_complexity(user_progress, current_mastery)
        
        # Create chat history entry
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message + file_info if file_info else message,
            response=ai_response,
            topic=main_topic,
            complexity_level=complexity_level,
            response_time=time.time() - start_time,
            preferred_pace=user_progress['learning_pace']
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
            
        db.session.commit()
        return jsonify({'message': 'Feedback submitted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/learning_report', methods=['GET'])
@token_required
def get_learning_report(current_user):
    try:
        questionnaire = QuestionnaireResponse.query.filter_by(user_id=current_user.id).first()
        user_progress = analyze_user_progress(current_user.id)
        
        progress_data = {
            'email': current_user.email,
            'progress': calculate_user_progress(current_user.id),
            'completed_questions': get_completed_questions_count(current_user.id),
            'learning_style': current_user.user_type,
            'learning_difficulty': questionnaire.learning_difficulty if questionnaire else None,
            'mastery_scores': user_progress.get('mastery_scores', {}),
            'preferred_topics': user_progress.get('preferred_topics', []),
            'understanding_level': user_progress.get('understanding_level', 0),
            'learning_pace': user_progress.get('learning_pace', 'normal'),
        }
        return jsonify(progress_data), 200
    except Exception as e:
        return jsonify({'error': f'Error generating learning report: {str(e)}'}), 500
