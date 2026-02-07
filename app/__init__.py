from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import Config

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    jwt.init_app(app)
    
    # Register blueprints
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.routes.patients import bp as patients_bp
    app.register_blueprint(patients_bp)
    
    from app.routes.reports import bp as reports_bp
    app.register_blueprint(reports_bp)
    
    from app.routes.observations import bp as observations_bp
    app.register_blueprint(observations_bp)
    
    from app.routes.documents import bp as documents_bp
    app.register_blueprint(documents_bp)
    
    from app.routes.fhir import bp as fhir_bp
    app.register_blueprint(fhir_bp)
    
    from app.routes.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp)
    
    from app.routes.backup import bp as backup_bp
    app.register_blueprint(backup_bp)
    
    from app.routes.ai import bp as ai_bp
    app.register_blueprint(ai_bp)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    return app