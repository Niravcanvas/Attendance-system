from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__)

@api_bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'API is running'})
