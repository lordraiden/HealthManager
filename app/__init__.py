from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import Config

db = SQLAlchemy()
jwt = JWTManager()


def create_app(config_class=Config):
    """
    Application factory pattern for creating Flask app instances.
    This allows for flexible configuration and testing.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Set instance path to handle read-only filesystems like Vercel
    app.instance_path = config_class.INSTANCE_PATH
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    return app


def register_blueprints(app):
    """Register all blueprints with the Flask application."""
    from app.routes.auth import bp as auth_bp
    from app.routes.patients import bp as patients_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.observations import bp as observations_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.fhir import bp as fhir_bp
    from app.routes.analytics import bp as analytics_bp
    from app.routes.backup import bp as backup_bp
    from app.routes.ai import bp as ai_bp
    from app.routes.settings import bp as settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(observations_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(fhir_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(settings_bp)