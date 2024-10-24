from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Create db instance without initializing
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    token = db.Column(db.String(500), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True, default=None)
    user_type = db.Column(db.String(20), nullable=True, default=None)
    questionnaire_completed = db.Column(db.Boolean, nullable=False, default=False)
    interaction_count = db.Column(db.Integer, default=0)  # Track total interactions

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Dimensión Temporal (20 puntos)
    study_time = db.Column(db.String(1))
    session_duration = db.Column(db.String(1))
    learning_pace = db.Column(db.String(1))
    
    # Dimensión Metodológica (30 puntos)
    learning_style = db.Column(db.String(1))
    content_format = db.Column(db.String(1))
    feedback_preference = db.Column(db.String(1))
    
    # Dimensión Motivacional (25 puntos)
    learning_goals = db.Column(db.String(1))
    motivators = db.Column(db.String(1))
    challenges = db.Column(db.String(1))
    
    # Dimensión de Contenido (25 puntos)
    interest_areas = db.Column(db.String(1))
    experience_level = db.Column(db.String(1))
    learning_tools = db.Column(db.String(1))
    
    # Learning Difficulties
    learning_difficulty = db.Column(db.String(20))
    tdah_aspects = db.Column(db.JSON)
    dyslexia_aspects = db.Column(db.JSON)
    
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    helpful = db.Column(db.Boolean, nullable=True)  # User feedback on response
    topic = db.Column(db.String(100))  # Topic classification
    complexity_level = db.Column(db.Integer)  # Track response complexity (1-5)
    user_understanding = db.Column(db.Integer)  # User comprehension level (1-5)
    
    # Fields for incremental learning
    response_time = db.Column(db.Float)  # Response time in seconds
    feedback_comments = db.Column(db.Text)  # Detailed user feedback
    learning_progress = db.Column(db.Float)  # Comprehension improvement (-1 to 1)
    mastery_level = db.Column(db.Float)  # Topic mastery level (0-1)
    session_duration = db.Column(db.Integer)  # Time spent on this interaction
    preferred_pace = db.Column(db.String(20))  # User's learning pace preference
    interaction_quality = db.Column(db.Float)  # Combined quality score (0-1)
    sentiment_score = db.Column(db.Float)  # Sentiment analysis of user messages (-1 to 1)
    engagement_score = db.Column(db.Float)  # User engagement level (0-1)
    concepts_covered = db.Column(db.JSON)  # Key concepts covered in the interaction
