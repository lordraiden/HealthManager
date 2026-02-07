from app import create_app

# Create the Flask app
app = create_app()

# Define the WSGI application object
wsgi_app = app

# Vercel expects the application to be exported as 'app'
app = wsgi_app

if __name__ == "__main__":
    app.run()