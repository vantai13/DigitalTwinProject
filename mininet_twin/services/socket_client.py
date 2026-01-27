# mininet_twin/services/socket_client.py
"""
SOCKET CLIENT - CẬP NHẬT VỚI GLOBAL INSTANCE
"""

import socketio
from utils.logger import setup_logger

logger = setup_logger()

# ========================================
# ✅ FIX: TẠO GLOBAL INSTANCE
# ========================================
socket_client_instance = None

class SocketClient:
    """
    Websocket client với command executor
    """
    def __init__(self, server_url, command_executor=None):
        global socket_client_instance
        
        self.server_url = server_url
        self.command_executor = command_executor
        
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=1,
            reconnection_delay_max=5
        )
        
        self._register_events()
        
        # ✅ LƯU INSTANCE GLOBAL
        socket_client_instance = self

    def set_command_executor(self, command_executor):
        self.command_executor = command_executor
        logger.info(">>> CommandExecutor attached")

    def _register_events(self):
        @self.sio.event
        def connect():
            logger.info("✅ Đã kết nối WebSocket!")

        @self.sio.event
        def connect_error(data):
            logger.error(f"❌ Lỗi kết nối: {data}")

        @self.sio.event
        def disconnect():
            logger.warning("⚠️ Mất kết nối WebSocket!")

        @self.sio.on('execute_command')
        def on_execute_command(data):
            logger.info(f"[SOCKET] Received command: {data.get('command')}")
            
            if not self.command_executor:
                logger.error("[SOCKET] CommandExecutor not set!")
                self.sio.emit('command_result', {
                    'success': False,
                    'action_id': data.get('action_id'),
                    'error': 'CommandExecutor not initialized'
                })
                return
            
            try:
                result = self.command_executor.execute(data)
                self.sio.emit('command_result', result)
                
                if result.get('success'):
                    logger.info(f"[SOCKET] Command OK: {data.get('action_id')}")
                else:
                    logger.warning(f"[SOCKET] Command failed: {result.get('error')}")
            
            except Exception as e:
                logger.error(f"[SOCKET] Error: {e}", exc_info=True)
                self.sio.emit('command_result', {
                    'success': False,
                    'action_id': data.get('action_id'),
                    'error': str(e)
                })
        # ========================================
        # ✅ THÊM: HANDLER CHO LINK STATUS UPDATE
        # ========================================
        @self.sio.on('force_link_status')
        def on_force_link_status(data):
            """
            Nhận lệnh force link status từ Backend
            
            Data format: {
                'link_id': 'h1-s1',
                'status': 'down'
            }
            """
            link_id = data.get('link_id')
            status = data.get('status')
            
            if not link_id or not status:
                logger.warning("[SOCKET] Missing link_id or status")
                return
            
            logger.info(f"[SOCKET] Force link status: {link_id} → {status}")
            
            try:
                from collectors.link_stats import update_link_status, reset_link_counter
                
                # Cập nhật status cache
                update_link_status(link_id, status)
                
                # Nếu link up → Reset counter
                if status == 'up':
                    reset_link_counter(link_id)
            
            except Exception as e:
                logger.error(f"[SOCKET] Error forcing link status: {e}")

    def connect(self):
        logger.info(f"🔌 Kết nối tới {self.server_url}...")
        try:
            self.sio.connect(self.server_url, wait_timeout=5)
            return True
        except Exception as e:
            logger.error(f"❌ Không thể kết nối: {e}")
            return False

    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()

    def send_telemetry(self, data):
        try:
            if self.sio.connected:
                self.sio.emit('mininet_telemetry', data)
        except Exception as e:
            logger.error(f"❌ Lỗi gửi: {e}")

    def is_connected(self):
        return self.sio.connected