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
    """
    Extract main topics from the input text using TF-IDF and POS tagging
    """
    try:
        # Tokenize and get POS tags
        tokens = word_tokenize(text.lower())
        pos_tags = nltk.pos_tag(tokens)
        
        # Filter for nouns and important words
        spanish_stopwords = set(stopwords.words('spanish'))
        important_words = [word for word, pos in pos_tags 
                         if word not in spanish_stopwords 
                         and pos.startswith(('NN', 'VB', 'JJ'))
                         and len(word) > 2]
        
        # Use TF-IDF to get important terms
        if not important_words:
            return ["general"]
            
        vectorizer = TfidfVectorizer(max_features=5)
        tfidf_matrix = vectorizer.fit_transform([' '.join(important_words)])
        
        # Get top terms
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        sorted_idx = np.argsort(scores)[::-1]
        
        topics = [feature_names[i] for i in sorted_idx[:3]]
        return topics if topics else ["general"]
    except Exception as e:
        print(f"Error extracting topics: {e}")
        return ["general"]

def analyze_user_progress(user_id):
    """
    Analyze user's learning progress and preferences
    """
    try:
        # Get user's questionnaire response
        questionnaire = QuestionnaireResponse.query.filter_by(user_id=user_id).first()
        
        # Get chat history
        chat_history = ChatHistory.query.filter_by(user_id=user_id).all()
        
        # Initialize progress data
        progress = {
            'total_interactions': len(chat_history),
            'mastery_scores': {},
            'learning_pace': 'moderate',
            'preferred_topics': set(),
            'average_understanding': 0
        }
        
        if questionnaire:
            # Map learning pace from questionnaire
            pace_mapping = {
                'A': 'slow',
                'B': 'moderate',
                'C': 'fast',
                'D': 'variable'
            }
            progress['learning_pace'] = pace_mapping.get(questionnaire.learning_pace, 'moderate')
        
        # Analyze chat history
        if chat_history:
            understanding_scores = []
            for chat in chat_history:
                # Track topics
                if chat.topic:
                    progress['preferred_topics'].add(chat.topic)
                    
                # Update mastery scores
                if chat.topic and chat.user_understanding:
                    current_score = progress['mastery_scores'].get(chat.topic, 0)
                    new_score = (current_score + chat.user_understanding/5.0) / 2
                    progress['mastery_scores'][chat.topic] = new_score
                
                if chat.user_understanding:
                    understanding_scores.append(chat.user_understanding)
            
            if understanding_scores:
                progress['average_understanding'] = sum(understanding_scores) / len(understanding_scores)
        
        progress['preferred_topics'] = list(progress['preferred_topics'])
        return progress
    except Exception as e:
        print(f"Error analyzing user progress: {e}")
        return {
            'total_interactions': 0,
            'mastery_scores': {},
            'learning_pace': 'moderate',
            'preferred_topics': [],
            'average_understanding': 0
        }

def find_similar_questions(query, user_id):
    """
    Find similar previous questions from the user's chat history
    """
    try:
        # Get user's chat history
        history = ChatHistory.query.filter_by(user_id=user_id).all()
        if not history:
            return []
        
        # Prepare messages for comparison
        messages = [chat.message for chat in history]
        if not messages:
            return []
            
        # Calculate similarity using TF-IDF and cosine similarity
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([query] + messages)
        
        # Calculate similarity scores
        similarity_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        
        # Get top 3 similar interactions
        similar_indices = similarity_scores.argsort()[::-1][:3]
        similar_interactions = [
            {
                'message': history[idx].message,
                'response': history[idx].response,
                'similarity': similarity_scores[idx]
            }
            for idx in similar_indices if similarity_scores[idx] > 0.3
        ]
        
        return similar_interactions
    except Exception as e:
        print(f"Error finding similar questions: {e}")
        return []

def get_tailored_prompt(user_type, message, user_progress, similar_interactions):
    """
    Generate a context-aware prompt based on user type and history
    """
    # Base prompt structure
    system_message = {
        "ESTRUCTURADO": "Eres un tutor que proporciona explicaciones detalladas y sistemáticas, con ejemplos paso a paso.",
        "EXPLORADOR": "Eres un guía que fomenta el descubrimiento y proporciona múltiples perspectivas y conexiones.",
        "INTENSIVO": "Eres un mentor que se enfoca en aplicaciones prácticas y resultados concretos."
    }.get(user_type, "Eres un tutor adaptativo que personaliza sus respuestas según las necesidades del estudiante.")
    
    # Add learning context
    context = f"\nEl estudiante tiene un ritmo de aprendizaje {user_progress['learning_pace']} "
    context += f"y ha completado {user_progress['total_interactions']} interacciones previas. "
    
    if similar_interactions:
        context += "\nHay preguntas similares previas que pueden ser relevantes."
    
    # Create the message list
    messages = [
        ChatMessage(role="system", content=system_message + context),
        ChatMessage(role="user", content=message)
    ]
    
    return messages

def calculate_response_complexity(user_progress, current_mastery):
    """
    Calculate appropriate complexity level for the response
    """
    try:
        # Base complexity on mastery and total interactions
        base_complexity = 1 + min(current_mastery * 2, 3)  # Scale 1-4
        
        # Adjust based on total interactions
        interaction_bonus = min(user_progress['total_interactions'] / 10, 1)  # Max +1
        
        # Adjust based on average understanding
        understanding_factor = user_progress.get('average_understanding', 0) / 5  # 0-1 scale
        
        # Calculate final complexity
        complexity = base_complexity + interaction_bonus
        complexity *= (0.7 + 0.3 * understanding_factor)  # Slight adjustment based on understanding
        
        # Ensure within bounds 1-5
        return max(1, min(5, round(complexity)))
    except Exception as e:
        print(f"Error calculating complexity: {e}")
        return 1

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    try:
        start_time = time.time()
        message = request.form.get('message', '')
        file = request.files.get('file')
        
        if not message and not file:
            return jsonify({'error': 'No se proporcionó ningún mensaje o archivo'}), 400
        
        file_info = ""
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_info = f"\nArchivo adjunto: {filename}"
        
        full_message = message + file_info if file_info else message
        
        # Extract topics and get main topic
        topics = extract_topics(full_message)
        main_topic = topics[0] if topics else "general"
        
        # Get user progress and similar interactions
        user_progress = analyze_user_progress(current_user.id)
        similar_interactions = find_similar_questions(message, current_user.id)
        current_mastery = user_progress['mastery_scores'].get(main_topic, 0)
        
        # Get tailored prompt and generate response
        messages = get_tailored_prompt(
            current_user.user_type, 
            full_message,
            user_progress,
            similar_interactions
        )
        
        chat_response = mistral_client.chat(
            model="mistral-tiny",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        ai_response = chat_response.choices[0].message.content
        
        # Calculate complexity and create chat history
        complexity_level = calculate_response_complexity(user_progress, current_mastery)
        
        chat_entry = ChatHistory(
            user_id=current_user.id,
            message=full_message,
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
        print(f"Error in chat endpoint: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chat_feedback', methods=['POST'])
@token_required
def chat_feedback(current_user):
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        helpful = data.get('helpful')
        understanding = data.get('understanding')
        
        if not chat_id:
            return jsonify({'error': 'Chat ID is required'}), 400
            
        chat_entry = ChatHistory.query.get(chat_id)
        if not chat_entry or chat_entry.user_id != current_user.id:
            return jsonify({'error': 'Chat entry not found'}), 404
            
        if helpful is not None:
            chat_entry.helpful = helpful
            
        if understanding is not None:
            chat_entry.user_understanding = understanding
            
        db.session.commit()
        return jsonify({'message': 'Feedback received'}), 200
        
    except Exception as e:
        print(f"Error in chat feedback: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/learning_report', methods=['GET'])
@token_required
def get_learning_report(current_user):
    try:
        questionnaire = QuestionnaireResponse.query.filter_by(user_id=current_user.id).first()
        user_progress = analyze_user_progress(current_user.id)
        chat_history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).first()
        
        # Calculate time spent (in hours)
        total_time = sum([chat.session_duration or 0 for chat in ChatHistory.query.filter_by(user_id=current_user.id).all()]) / 3600
        
        # Get session count
        session_count = ChatHistory.query.filter_by(user_id=current_user.id).count()
        
        progress_data = {
            'email': current_user.email,
            'progress': calculate_user_progress(current_user.id),
            'learning_style': current_user.user_type,
            'learning_difficulty': questionnaire.learning_difficulty if questionnaire else None,
            'total_time': round(total_time, 1),
            'session_count': session_count,
            'last_session': chat_history.timestamp.strftime('%Y-%m-%d %H:%M:%S') if chat_history else None,
            'streak': calculate_streak(current_user.id)
        }
        return jsonify(progress_data), 200
    except Exception as e:
        print(f"Error generating learning report: {str(e)}")
        return jsonify({'error': f'Error generating learning report: {str(e)}'}), 500

def calculate_user_progress(user_id):
    try:
        # Get total possible interactions (questionnaire responses + chat history)
        total_possible = 5  # Base progress from questionnaire
        questionnaire = QuestionnaireResponse.query.filter_by(user_id=user_id).first()
        if questionnaire:
            total_possible += 5  # Additional progress for completing questionnaire
        
        # Calculate actual progress
        progress = 0
        if questionnaire:
            progress += 5  # Base progress for having questionnaire data
            # Add progress for each completed section
            if questionnaire.learning_style:
                progress += 1
            if questionnaire.learning_difficulty:
                progress += 1
            if questionnaire.content_format:
                progress += 1
            if questionnaire.feedback_preference:
                progress += 1
            if questionnaire.learning_goals:
                progress += 1
        
        # Calculate percentage
        return min(100, int((progress / total_possible) * 100))
    except Exception as e:
        print(f"Error calculating user progress: {str(e)}")
        return 0

def calculate_streak(user_id):
    try:
        chat_history = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).all()
        if not chat_history:
            return 0
            
        streak = 0
        current_date = datetime.now().date()
        last_date = None
        
        for chat in chat_history:
            chat_date = chat.timestamp.date()
            if last_date is None:
                last_date = chat_date
                streak = 1
            elif (last_date - chat_date).days == 1:
                streak += 1
                last_date = chat_date
            else:
                break
                
        return streak
    except Exception as e:
        print(f"Error calculating streak: {str(e)}")
        return 0
