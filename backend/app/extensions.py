# backend/app/extensions.py
from flask_socketio import SocketIO
from threading import Lock

# Import từ vị trí mới của models
from app.models.network_model import NetworkModel

# 1. Khởi tạo SocketIO (Chưa gắn app, chỉ tạo object)
# Từ app.py cũ: socketio = SocketIO(..., cors_allowed_origins="*", async_mode='threading', ...)
socketio = SocketIO(
    cors_allowed_origins="*", 
    async_mode='threading',
    logger=True,
    engineio_logger=True
)

# 2. Khởi tạo Digital Twin (Biến toàn cục dùng chung)
# Từ app.py cũ: digital_twin = NetworkModel("Main Digital Twin")
digital_twin = NetworkModel("Main Digital Twin")

# 3. Khởi tạo Lock
# Từ app.py cũ: data_lock = Lock()
data_lock = Lock()