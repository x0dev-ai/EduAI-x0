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
import time
from werkzeug.utils import secure_filename

# Create NLTK data directory and setup
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

class IncrementalLearningSystem:
    def __init__(self):
        self.topic_mastery_threshold = 0.8
        self.complexity_levels = {
            1: "básico",
            2: "intermedio",
            3: "avanzado",
            4: "experto",
            5: "maestro"
        }
        
    def calculate_topic_mastery(self, chat_history):
        """Calculate mastery level for each topic based on user interactions"""
        topic_scores = {}
        
        for chat in chat_history:
            if chat.topic not in topic_scores:
                topic_scores[chat.topic] = []
            
            # Calculate interaction score based on multiple factors
            understanding_score = chat.user_understanding / 5.0 if chat.user_understanding else 0.6
            helpful_bonus = 0.2 if chat.helpful else -0.1
            complexity_factor = chat.complexity_level / 5.0 if chat.complexity_level else 0.5
            
            interaction_score = (understanding_score + helpful_bonus) * complexity_factor
            topic_scores[chat.topic].append(interaction_score)
        
        # Calculate weighted average for each topic
        topic_mastery = {}
        for topic, scores in topic_scores.items():
            if scores:
                # Recent scores have more weight
                weights = np.exp(np.linspace(-1, 0, len(scores)))
                weights = weights / weights.sum()
                topic_mastery[topic] = np.average(scores, weights=weights)
            else:
                topic_mastery[topic] = 0.0
                
        return topic_mastery
    
    def adjust_complexity(self, current_complexity, understanding_trend, success_rate):
        """Adjust content complexity based on user performance"""
        if understanding_trend > 0.2 and success_rate > 0.7:
            return min(current_complexity + 1, 5)
        elif understanding_trend < -0.2 or success_rate < 0.3:
            return max(current_complexity - 1, 1)
        return current_complexity
    
    def generate_learning_path(self, user_id, target_topic=None):
        """Generate personalized learning path based on user's progress"""
        recent_chats = ChatHistory.query.filter_by(user_id=user_id)\
            .order_by(ChatHistory.timestamp.desc())\
            .limit(50).all()
            
        if not recent_chats:
            return {
                'current_level': 1,
                'recommended_topics': [],
                'next_complexity': 1
            }
            
        # Calculate topic mastery and performance metrics
        topic_mastery = self.calculate_topic_mastery(recent_chats)
        
        # Calculate understanding trend
        understanding_scores = [chat.user_understanding for chat in recent_chats if chat.user_understanding]
        understanding_trend = 0
        if len(understanding_scores) > 1:
            understanding_trend = np.polyfit(range(len(understanding_scores)), understanding_scores, 1)[0]
        
        # Calculate success rate
        success_rate = sum(1 for chat in recent_chats if chat.helpful) / len(recent_chats)
        
        # Current complexity level
        current_complexity = recent_chats[0].complexity_level or 1
        
        # Adjust complexity based on performance
        next_complexity = self.adjust_complexity(current_complexity, understanding_trend, success_rate)
        
        # Identify topics needing attention
        weak_topics = [topic for topic, mastery in topic_mastery.items() 
                      if mastery < self.topic_mastery_threshold]
        
        # Generate recommended topics
        recommended_topics = []
        if target_topic:
            recommended_topics.append(target_topic)
        recommended_topics.extend(weak_topics)
        
        return {
            'current_level': current_complexity,
            'recommended_topics': recommended_topics[:3],
            'next_complexity': next_complexity,
            'topic_mastery': topic_mastery
        }

# Initialize incremental learning system
learning_system = IncrementalLearningSystem()

def extract_topics(text):
    """Extract topics from text using NLP"""
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
    """Find similar previous questions using TF-IDF and cosine similarity"""
    history = ChatHistory.query.filter_by(
        user_id=user_id,
        helpful=True
    ).order_by(ChatHistory.timestamp.desc()).all()
    
    if not history:
        return []
    
    previous_questions = [chat.message for chat in history]
    
    try:
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
                    'similarity': similarities[idx],
                    'understanding': history[idx].user_understanding
                })
        
        return similar_interactions
    except Exception as e:
        print(f"Error finding similar questions: {e}")
        return []

def get_tailored_prompt(user_type, message, learning_path, similar_interactions):
    """Generate a tailored prompt based on user type and learning progress"""
    base_system_prompt = '''
    Eres un tutor de IA especializado en educación adaptativa. Debes responder en español y adaptar tu estilo según el perfil del estudiante.
    '''
    
    complexity_info = f"\nNivel de complejidad actual: {learning_path['current_level']}/5"
    mastery_info = "\nDominio por tema:\n"
    for topic, mastery in learning_path.get('topic_mastery', {}).items():
        mastery_info += f"- {topic}: {mastery:.2f}/1.0\n"
    
    recommendations = "\nTemas recomendados para fortalecer:\n"
    for topic in learning_path.get('recommended_topics', []):
        recommendations += f"- {topic}\n"
    
    context = "\nInteracciones previas relevantes:\n"
    for idx, interaction in enumerate(similar_interactions, 1):
        context += f"{idx}. Pregunta similar: {interaction['question']}\n"
        context += f"   Respuesta exitosa: {interaction['response']}\n"
        context += f"   Nivel de comprensión: {interaction.get('understanding', 3)}/5\n"
    
    if user_type == 'ESTRUCTURADO':
        system_prompt = base_system_prompt + f'''
        Para estudiantes estructurados:
        - Proporciona explicaciones detalladas y analíticas
        - Incluye referencias académicas cuando sea relevante
        - Usa un enfoque sistemático y progresivo
        {complexity_info}
        {mastery_info}
        {recommendations}
        {context}
        '''
    elif user_type == 'EXPLORADOR':
        system_prompt = base_system_prompt + f'''
        Para estudiantes exploradores:
        - Ofrece explicaciones interactivas y prácticas
        - Fomenta el descubrimiento y la experimentación
        - Proporciona ejemplos variados y creativos
        {complexity_info}
        {mastery_info}
        {recommendations}
        {context}
        '''
    else:  # INTENSIVO
        system_prompt = base_system_prompt + f'''
        Para estudiantes intensivos:
        - Da explicaciones concisas y directas
        - Usa ejemplos de la vida real
        - Divide la información en pasos pequeños
        {complexity_info}
        {mastery_info}
        {recommendations}
        {context}
        '''
    
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Responde a la siguiente consulta: {message}")
    ]

def preprocess_text(text):
    """Preprocess input text"""
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

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    start_time = time.time()
    message = request.form.get('message', '')
    file = request.files.get('file')
    
    if not message and not file:
        return jsonify({'error': 'No se proporcionó ningún mensaje o archivo'}), 400
        
    # Handle file if present
    file_info = ""
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_info = f"\nArchivo adjunto: {filename}"
        
    # Preprocess the input message
    processed_message = preprocess_text(message + file_info if file_info else message)
    
    # Extract topics and find similar questions
    topics = extract_topics(processed_message)
    main_topic = topics[0] if topics else "general"
    similar_interactions = find_similar_questions(processed_message, current_user.id)
    
    # Get personalized learning path
    learning_path = learning_system.generate_learning_path(current_user.id, main_topic)
    
    # Get tailored prompt based on user type and learning path
    messages = get_tailored_prompt(
        current_user.user_type,
        processed_message,
        learning_path,
        similar_interactions
    )

    try:
        chat_response = mistral_client.chat(
            model="mistral-tiny",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        ai_response = chat_response.choices[0].message.content
        
        # Update user interaction count
        current_user.interaction_count += 1
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Save the chat history with enhanced tracking
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=message + file_info if file_info else message,
            response=ai_response,
            complexity_level=learning_path['next_complexity'],
            topic=main_topic,
            response_time=response_time,
            mastery_level=learning_path['topic_mastery'].get(main_topic, 0.0)
        )
        db.session.add(chat_entry)
        db.session.commit()

        return jsonify({
            'response': ai_response,
            'chat_id': chat_entry.id,
            'complexity_level': learning_path['next_complexity']
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

@chatbot_bp.route('/learning_report', methods=['GET'])
@token_required
def get_learning_report(current_user):
    """Get detailed learning progress report"""
    try:
        learning_path = learning_system.generate_learning_path(current_user.id)
        return jsonify({
            'current_level': learning_path['current_level'],
            'recommended_topics': learning_path['recommended_topics'],
            'topic_mastery': learning_path['topic_mastery']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
