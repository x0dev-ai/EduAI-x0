from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    token = db.Column(db.String(500), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True, default=None)
    user_type = db.Column(db.String(20), nullable=True, default=None)
    questionnaire_completed = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Dimensión Temporal
    study_time = db.Column(db.String(1))
    session_duration = db.Column(db.String(1))
    learning_pace = db.Column(db.String(1))
    
    # Dimensión Metodológica
    learning_style = db.Column(db.String(1))
    content_format = db.Column(db.String(1))
    feedback_preference = db.Column(db.String(1))
    
    # Dimensión Motivacional
    learning_goals = db.Column(db.String(1))
    motivators = db.Column(db.String(1))
    challenges = db.Column(db.String(1))
    
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
