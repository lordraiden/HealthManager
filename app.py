from app import create_app
from app.models import db


def create_and_setup_app():
    """Create the Flask application and initialize database tables."""
    app = create_app()
    
    # Create database tables if they don't exist
    with app.app_context():
        from app.models import Patient, User
        from app.routes.auth import init_default_user
        db.create_all()
        init_default_user()
    
    return app


if __name__ == "__main__":
    app = create_and_setup_app()
    app.run()