from app import create_app
from config import Config
import os

# Initialize directories
Config.init_directories()

app = create_app()

if __name__ == '__main__':
    app.run(
        host=app.config.get('HOST', '127.0.0.1'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )