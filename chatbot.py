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
