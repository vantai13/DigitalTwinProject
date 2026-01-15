
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from app.extensions import socketio, action_logger_service
from app.api.topology import topology_bp
from app.api.device_updates import device_bp
from app.events.socket_events import register_socket_events
from app.services.monitor_service import start_monitoring_service
from app.utils.logger import get_logger

load_dotenv()

logger = get_logger()

def create_app():
    app = Flask(__name__)
    
    # Load cấu hình
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))
    
    # CORS Configuration
    cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS(app, resources={r"/*": {"origins": cors_origins}})

    # Socket.IO Configuration
    socketio_cors = os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS', '*')
    async_mode = os.getenv('SOCKETIO_ASYNC_MODE', 'eventlet')
    
    socketio.init_app(
        app, 
        async_mode=async_mode, 
        cors_allowed_origins=socketio_cors
    )

    # ========================================
    # ✅ FIX: ATTACH SOCKETIO TRƯỚC KHI REGISTER BLUEPRINT
    # ========================================
    action_logger_service.set_socketio(socketio)
    logger.info(">>> ActionLogger attached to SocketIO")

    # ✅ SAU ĐÓ MỚI REGISTER BLUEPRINT
    app.register_blueprint(topology_bp, url_prefix='/api')
    app.register_blueprint(device_bp, url_prefix='/api')
    
    # Register Control Blueprint
    from app.api.control import control_bp
    app.register_blueprint(control_bp, url_prefix='/api')
    logger.info(">>> Control API endpoints registered")
    
    # Register Test Control Blueprint (DEBUG mode only)
    if app.config['DEBUG']:
        from app.api.test_control import test_control_bp
        app.register_blueprint(test_control_bp, url_prefix='/api')
        logger.info(">>> Test Control endpoints registered (DEBUG mode)")

    # Register Socket Events
    register_socket_events(socketio)
    
    # Start Background Services
    start_monitoring_service()

    logger.info(">>> Flask App initialized successfully!")
    return app