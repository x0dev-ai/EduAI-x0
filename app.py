import os
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "eduai_companion_secret_key"

# Register blueprints
from auth import auth_bp
from questionnaire import questionnaire_bp
from chatbot import chatbot_bp

app.register_blueprint(auth_bp)
app.register_blueprint(questionnaire_bp)
app.register_blueprint(chatbot_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/questionnaire')
def questionnaire_view():
    return render_template('questionnaire.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
