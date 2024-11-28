import os
import nltk
from flask import Blueprint, request, jsonify
from models import User
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
        nltk.download('spanish_grammars', download_dir=nltk_data_dir, quiet=True)
        nltk.download('maxent_ne_chunker', download_dir=nltk_data_dir, quiet=True)
        nltk.download('words', download_dir=nltk_data_dir, quiet=True)
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
        try:
            tokens = word_tokenize(text.lower())
            pos_tags = nltk.pos_tag(tokens)
            
            spanish_stopwords = set(stopwords.words('spanish'))
            important_words = [word for word, pos in pos_tags 
                             if word not in spanish_stopwords 
                             and pos.startswith(('NN', 'VB', 'JJ'))
                             and len(word) > 2]
        except Exception as e:
            print(f"NLTK processing failed, falling back to basic tokenization: {e}")
            words = text.lower().split()
            important_words = [word for word in words if len(word) > 2]
        
        if not important_words:
            return ["general"]
            
        vectorizer = TfidfVectorizer(max_features=5)
        tfidf_matrix = vectorizer.fit_transform([' '.join(important_words)])
        
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        sorted_idx = np.argsort(scores)[::-1]
        
        topics = [feature_names[i] for i in sorted_idx[:3]]
        return topics if topics else ["general"]
    except Exception as e:
        print(f"Error extracting topics: {e}")
        return ["general"]

def get_tailored_prompt(user_type, message):
    system_message = {
        "ESTRUCTURADO": "Eres un tutor que proporciona explicaciones detalladas y sistemáticas, con ejemplos paso a paso.",
        "EXPLORADOR": "Eres un guía que fomenta el descubrimiento y proporciona múltiples perspectivas y conexiones.",
        "INTENSIVO": "Eres un mentor que se enfoca en aplicaciones prácticas y resultados concretos."
    }.get(user_type, "Eres un tutor adaptativo que personaliza sus respuestas según las necesidades del estudiante.")
    
    messages = [
        ChatMessage(role="system", content=system_message),
        ChatMessage(role="user", content=message)
    ]
    
    return messages

@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat(current_user):
    try:
        start_time = time.time()
        message = request.form.get('message', '')
        file = request.files.get('file')
        user_type = request.form.get('user_type', 'ESTRUCTURADO')
        
        if not message and not file:
            return jsonify({'error': 'No se proporcionó ningún mensaje o archivo'}), 400
        
        file_info = ""
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_info = f"\nArchivo adjunto: {filename}"
        
        full_message = message + file_info if file_info else message
        
        topics = extract_topics(full_message)
        main_topic = topics[0] if topics else "general"
        
        messages = get_tailored_prompt(user_type, full_message)
        
        chat_response = mistral_client.chat(
            model="mistral-tiny",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        ai_response = chat_response.choices[0].message.content
        
        chat_data = {
            'message': full_message,
            'response': ai_response,
            'topic': main_topic,
            'timestamp': datetime.now().isoformat(),
            'response_time': time.time() - start_time
        }
        
        return jsonify({
            'response': ai_response,
            'chat_data': chat_data
        }), 200
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/chat_feedback', methods=['POST'])
@token_required
def chat_feedback(current_user):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        return jsonify({
            'message': 'Feedback received',
            'feedback_data': data
        }), 200
        
    except Exception as e:
        print(f"Error in chat feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chatbot_bp.route('/learning_report', methods=['GET'])
@token_required
def get_learning_report(current_user):
    try:
        return jsonify({
            'email': current_user['email'],
            'message': 'Learning data should be retrieved from localStorage'
        }), 200
    except Exception as e:
        print(f"Error generating learning report: {str(e)}")
        return jsonify({'error': f'Error generating learning report: {str(e)}'}), 500