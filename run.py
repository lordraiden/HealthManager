from app import create_app, db
from app.models import Patient, User
from app.routes.auth import init_default_user
from config import Config
import os

app = create_app()


@app.before_first_request
def create_tables():
    """Create database tables if they don't exist"""
    db.create_all()
    init_default_user()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_user()
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )