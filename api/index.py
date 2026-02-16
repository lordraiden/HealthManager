import os
from app import create_app

# Set instance path to handle read-only filesystems like Vercel
os.environ.setdefault('INSTANCE_PATH', '/tmp/instance')

# Create the Flask app
app = create_app()

# Vercel expects the application to be exported as 'app'
application = app

if __name__ == "__main__":
    app.run()