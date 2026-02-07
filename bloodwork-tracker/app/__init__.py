from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import Config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')

    from app.routes.patients import bp as patients_bp
    app.register_blueprint(patients_bp, url_prefix='/api/v1/patients')

    from app.routes.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/api/v1/reports')

    from app.routes.observations import bp as observations_bp
    app.register_blueprint(observations_bp, url_prefix='/api/v1/observations')

    from app.routes.documents import bp as documents_bp
    app.register_blueprint(documents_bp, url_prefix='/api/v1/documents')

    from app.routes.fhir import bp as fhir_bp
    app.register_blueprint(fhir_bp, url_prefix='/fhir')

    from app.routes.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/api/v1/analytics')

    from app.routes.backup import bp as backup_bp
    app.register_blueprint(backup_bp, url_prefix='/api/v1/backup')

    from app.routes.ai import bp as ai_bp
    app.register_blueprint(ai_bp, url_prefix='/api/v1/ai')

    return app