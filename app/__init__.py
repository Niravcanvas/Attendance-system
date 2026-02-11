"""
Flask Application Factory
"""
from flask import Flask
from app.config import config
from app.services.face_recognition import FaceRecognitionService


# Global face recognition service
face_service = None


def create_app(config_name='default'):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize face recognition service
    global face_service
    face_service = FaceRecognitionService(app.config)
    face_service.initialize()
    
    # Add custom Jinja2 filters
    @app.template_filter('js_escape')
    def js_escape_filter(value):
        """Escape string for JavaScript"""
        if not value:
            return ''
        import json
        return json.dumps(str(value))[1:-1]
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.capture import capture_bp
    from app.routes.students import students_bp
    from app.routes.subjects import subjects_bp
    from app.routes.sessions import sessions_bp
    from app.routes.attendance import attendance_bp
    from app.routes.users import users_bp
    from app.routes.api import api_bp
    
    # Register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(capture_bp)
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(subjects_bp, url_prefix='/subjects')
    app.register_blueprint(sessions_bp, url_prefix='/sessions')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Also register main routes at root level for form submissions
    try:
        from app.routes.main import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass  # main_bp is optional
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return "Page not found", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return "Internal server error", 500
    
    return app


def get_face_service():
    """Get the global face recognition service"""
    return face_service