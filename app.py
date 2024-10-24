import os
from datetime import timedelta
from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from database import db

# create the app
app = Flask(__name__)

# setup configurations
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['JWT_SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# initialize extensions
db.init_app(app)
jwt = JWTManager(app)

# Register blueprints
from auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/api/auth')

@app.route('/')
def auth_page():
    return render_template('auth.html')

with app.app_context():
    import models
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
