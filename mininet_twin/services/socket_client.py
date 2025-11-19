import socketio
import config
from utils.logger import logger

class SocketClient:
    def __init__(self):
        self.sio = socketio.Client()
        self._setup_events()

    def _setup_events(self):
        @self.sio.event
        def connect():
            logger.info("WebSocket đã kết nối!")
        
        @self.sio.event
        def disconnect():
            logger.warning("Mất kết nối WebSocket!")

    def connect(self):
        try:
            self.sio.connect(config.SOCKET_URL, wait_timeout=5)
            return True
        except Exception as e:
            logger.error(f"Lỗi kết nối Socket: {e}")
            return False

    def send_telemetry(self, data):
        if self.sio.connected:
            try:
                self.sio.emit('mininet_telemetry', data)
            except Exception as e:
                logger.error(f"Lỗi gửi dữ liệu: {e}")

    def close(self):
        if self.sio.connected:
            self.sio.disconnect()