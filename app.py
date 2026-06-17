import os, secrets
from flask import Flask

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Register blueprints
from routes.dashboard import bp as dash_bp
from routes.tasks import bp as tasks_bp
from routes.status import bp as status_bp
from routes.config_routes import bp as config_bp
from routes.auth import bp as auth_bp
from routes.habits import bp as habits_bp
app.register_blueprint(dash_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(status_bp)
app.register_blueprint(config_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(habits_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)