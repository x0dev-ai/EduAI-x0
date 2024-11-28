from datetime import datetime
import json

class LocalStorageModel:
    @staticmethod
    def to_dict(obj):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

class User:
    def __init__(self, email, token=None, password_hash=None, user_type=None):
        self.email = email
        self.token = token
        self.password_hash = password_hash
        self.user_type = user_type
        self.questionnaire_completed = False
        self.interaction_count = 0

    def to_dict(self):
        return LocalStorageModel.to_dict(self)

class QuestionnaireResponse:
    def __init__(self, user_id, **kwargs):
        self.user_id = user_id
        self.study_time = kwargs.get('study_time')
        self.session_duration = kwargs.get('session_duration')
        self.learning_pace = kwargs.get('learning_pace')
        self.learning_style = kwargs.get('learning_style')
        self.content_format = kwargs.get('content_format')
        self.feedback_preference = kwargs.get('feedback_preference')
        self.learning_goals = kwargs.get('learning_goals')
        self.motivators = kwargs.get('motivators')
        self.challenges = kwargs.get('challenges')
        self.interest_areas = kwargs.get('interest_areas')
        self.experience_level = kwargs.get('experience_level')
        self.learning_tools = kwargs.get('learning_tools')
        self.learning_difficulty = kwargs.get('learning_difficulty')
        self.tdah_responses = kwargs.get('tdah_responses')
        self.dyslexia_responses = kwargs.get('dyslexia_responses')

    def to_dict(self):
        return LocalStorageModel.to_dict(self)

class ChatHistory:
    def __init__(self, user_id, message, response, **kwargs):
        self.user_id = user_id
        self.message = message
        self.response = response
        self.timestamp = kwargs.get('timestamp', datetime.now().isoformat())
        self.helpful = kwargs.get('helpful')
        self.topic = kwargs.get('topic')
        self.complexity_level = kwargs.get('complexity_level')
        self.user_understanding = kwargs.get('user_understanding')
        self.response_time = kwargs.get('response_time')
        self.feedback_comments = kwargs.get('feedback_comments')
        self.learning_progress = kwargs.get('learning_progress')
        self.mastery_level = kwargs.get('mastery_level')
        self.session_duration = kwargs.get('session_duration')
        self.preferred_pace = kwargs.get('preferred_pace')
        self.interaction_quality = kwargs.get('interaction_quality')

    def to_dict(self):
        return LocalStorageModel.to_dict(self)
