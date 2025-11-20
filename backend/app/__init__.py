from flask import Flask
from flask_cors import CORS

from app.extensions import socketio
from app.api.topology import topology_bp
from app.api.device_updates import device_bp
from app.events.socket_events import register_socket_events
from app.services.monitor_service import start_monitoring_service
from app.utils.logger import get_logger

logger = get_logger()

def create_app():
    app = Flask(__name__)
    
    #  Cấu hình App
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config['SECRET_KEY'] = 'secret!'

    #  Khởi tạo Extensions với App
    # Quan trọng: Gắn socketio vào app tại đây
    socketio.init_app(app, async_mode='threading', cors_allowed_origins="*")

    #  Đăng ký Blueprints (REST API)
    # Mọi route trong topology_bp sẽ có prefix /api 
    app.register_blueprint(topology_bp, url_prefix='/api')
    app.register_blueprint(device_bp, url_prefix='/api')

    #  Đăng ký Socket Events
    register_socket_events(socketio)
    
    #. Khởi động Background Tasks (Reaper Thread)
    start_monitoring_service()

    logger.info(">>> Flask App đã được khởi tạo thành công qua Factory!")
    return app