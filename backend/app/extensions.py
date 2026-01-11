from flask_socketio import SocketIO
from threading import Lock


from app.models.network_model import NetworkModel
from app.services.action_logger import action_logger_service
#  Khởi tạo SocketIO (Chưa gắn app, chỉ tạo object)
socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode='threading',
    logger=True,
    engineio_logger=True
)

#  Khởi tạo Digital Twin (Biến toàn cục dùng chung)
digital_twin = NetworkModel("Main Digital Twin")

# Khởi tạo Lock
data_lock = Lock()