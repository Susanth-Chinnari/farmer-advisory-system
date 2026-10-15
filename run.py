"""
run.py - Main Server Entry Point

Beginner-Friendly Explanation:
This file creates and starts our Flask web application server.
It sets up the frontend static file delivery (HTML, CSS, JavaScript),
registers our backend API blueprints, configures upload security limits,
and automatically initializes the SQLite database tables on startup.
"""

import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, render_template

from backend.config import (
    BASE_DIR,
    SECRET_KEY,
    MAX_CONTENT_LENGTH,
    UPLOAD_FOLDER
)
from backend.database import init_db
from backend.auth import auth_bp
from backend.routes import api_bp


def create_app(test_config=None):
    """
    Application Factory:
    Builds and configures the Flask application.
    Using a factory function makes testing with pytest simple and clean.
    """
    frontend_dir = BASE_DIR / 'frontend'

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path='',
        template_folder=str(frontend_dir)
    )

    # Core Security Configuration
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    if test_config:
        app.config.update(test_config)

    # Ensure database tables exist
    with app.app_context():
        init_db()

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    # -----------------------------------------------------------------------
    # Frontend Page Routes
    # -----------------------------------------------------------------------
    @app.route('/')
    def serve_index():
        """Serves the main farmer advisory dashboard."""
        return send_from_directory(str(frontend_dir), 'index.html')

    @app.route('/login')
    def serve_login():
        """Serves the farmer authentication portal."""
        return send_from_directory(str(frontend_dir), 'login.html')

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        """Safely serves uploaded crop photographs."""
        return send_from_directory(str(UPLOAD_FOLDER), filename)

    # -----------------------------------------------------------------------
    # Global Error Handlers (Beginner-Friendly JSON responses)
    # -----------------------------------------------------------------------
    @app.errorhandler(413)
    def file_too_large(error):
        """Catches uploads exceeding MAX_CONTENT_LENGTH (e.g. > 5MB)."""
        return jsonify({
            'success': False,
            'error': 'File is too large. Please upload an image under 5 MB.'
        }), 413

    @app.errorhandler(404)
    def not_found(error):
        """Handles missing routes gracefully."""
        return jsonify({
            'success': False,
            'error': 'The requested resource was not found.'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Catches unexpected server exceptions without leaking stack trace."""
        return jsonify({
            'success': False,
            'error': 'An internal server error occurred. Please try again later.'
        }), 500

    return app


if __name__ == '__main__':
    # Initialize app and run development server on port 5000
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    print("\n=======================================================")
    print(" 🌾 AI-Based Farmer Query Support and Advisory System")
    print(f" 🚀 Server running at: http://127.0.0.1:{port}")
    print("=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=True)
