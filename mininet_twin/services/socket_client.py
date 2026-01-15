# mininet_twin/services/socket_client.py
"""
SOCKET CLIENT - CẬP NHẬT
-------------------------
[THÊM] Tích hợp Command Executor để nhận và thực thi lệnh từ Backend
"""

import socketio
from utils.logger import setup_logger

logger = setup_logger()

class SocketClient:
    """
    Websocket client - CẬP NHẬT VỚI COMMAND EXECUTOR
    """
    def __init__(self, server_url, command_executor=None):
        """
        Args:
            server_url: URL của Backend
            command_executor: CommandExecutor instance (optional)
        """
        self.server_url = server_url
        self.command_executor = command_executor  # ← MỚI THÊM
        
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # Infinite
            reconnection_delay=1,
            reconnection_delay_max=5
        )
        
        # Đăng ký các sự kiện
        self._register_events()

    def set_command_executor(self, command_executor):
        """
        Set CommandExecutor sau khi khởi tạo
        (Dùng khi executor được tạo sau SocketClient)
        """
        self.command_executor = command_executor
        logger.info(">>> CommandExecutor attached to SocketClient")

    def _register_events(self):
        @self.sio.event
        def connect():
            logger.info("✅ Đã kết nối WebSocket tới Backend!")

        @self.sio.event
        def connect_error(data):
            logger.error(f"❌ Lỗi kết nối WebSocket: {data}")

        @self.sio.event
        def disconnect():
            logger.warning("⚠️  Mất kết nối WebSocket!")

        # ========================================
        # [MỚI] NHẬN LỆNH TỪ BACKEND
        # ========================================
        @self.sio.on('execute_command')
        def on_execute_command(data):
            """
            Nhận lệnh từ Backend và thực thi
            
            Args:
                data (dict): {
                    'action_id': 'act_123',
                    'command': 'toggle_device',
                    'data': {...}
                }
            """
            logger.info(f"[SOCKET] Received command: {data.get('command')} | Action: {data.get('action_id')}")
            
            if not self.command_executor:
                logger.error("[SOCKET] CommandExecutor not set! Cannot execute command.")
                # Gửi error result về Backend
                self.sio.emit('command_result', {
                    'success': False,
                    'action_id': data.get('action_id'),
                    'error': 'CommandExecutor not initialized'
                })
                return
            
            try:
                # Thực thi lệnh
                result = self.command_executor.execute(data)
                
                # Gửi kết quả về Backend
                self.sio.emit('command_result', result)
                
                if result.get('success'):
                    logger.info(f"[SOCKET] Command executed successfully: {data.get('action_id')}")
                else:
                    logger.warning(f"[SOCKET] Command failed: {result.get('error')}")
            
            except Exception as e:
                logger.error(f"[SOCKET] Error executing command: {e}", exc_info=True)
                # Gửi error result
                self.sio.emit('command_result', {
                    'success': False,
                    'action_id': data.get('action_id'),
                    'error': str(e)
                })

    def connect(self):
        """Kết nối tới Server"""
        logger.info(f"🔌 Kết nối tới {self.server_url}...")
        try:
            self.sio.connect(self.server_url, wait_timeout=5)
            return True
        except Exception as e:
            logger.error(f"❌ Không thể kết nối SocketIO: {e}")
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
            logger.error(f"❌ Lỗi gửi WebSocket: {e}")

    def is_connected(self):
        return self.sio.connected