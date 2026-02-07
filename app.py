from app import create_app

app = create_app()

# Create database tables if they don't exist
with app.app_context():
    from app import db
    from app.models import Patient, User
    from app.routes.auth import init_default_user
    db.create_all()
    init_default_user()

if __name__ == "__main__":
    app.run()