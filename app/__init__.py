from flask import Flask
from flask_cors import CORS
import config

def create_app():
    """Application Factory Pattern"""
    app = Flask(__name__, static_folder=config.ASSET_FOLDER_NAME, static_url_path="/assets")
    CORS(app)

    with app.app_context():
        # Đăng ký các routes (endpoints) từ file routes.py
        from . import routes

    return app
