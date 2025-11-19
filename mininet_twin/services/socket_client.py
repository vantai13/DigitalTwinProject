import socketio
from utils.logger import setup_logger

logger = setup_logger()

class SocketClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.sio = socketio.Client()
        
        # Đăng ký các sự kiện ngay khi khởi tạo
        self._register_events()

    def _register_events(self):
        @self.sio.event
        def connect():
            logger.info("Đã kết nối WebSocket tới Backend!")

        @self.sio.event
        def connect_error(data):
            logger.error(f"Lỗi kết nối WebSocket: {data}")

        @self.sio.event
        def disconnect():
            logger.warning("Mất kết nối WebSocket!")

    def connect(self):
        """Kết nối tới Server"""
        logger.info(f" Kết nối tới {self.server_url}...")
        try:
            self.sio.connect(self.server_url, wait_timeout=5)
            return True
        except Exception as e:
            logger.error(f" Không thể kết nối SocketIO: {e}")
            return False

    def disconnect(self):
        """Ngắt kết nối an toàn"""
        if self.sio.connected:
            self.sio.disconnect()

    def send_telemetry(self, data):
        """Gửi dữ liệu đo đạc (metrics) lên Server"""
        try:
            if self.sio.connected:
                self.sio.emit('mininet_telemetry', data)
        except Exception as e:
            logger.error(f" Lỗi gửi WebSocket: {e}")

    def is_connected(self):
        return self.sio.connected