import threading
from sqlite3.dbapi2 import Timestamp
from flask import request
from flask_socketio import emit
from app.extensions import digital_twin, data_lock, action_logger_service  # ← Thêm import
from app.models.action_log import ActionStatus  # ← Thêm import
from app.utils.logger import get_logger
from app.services.influx_service import influx_service
import queue
import time

logger = get_logger()


# --- 1. KHỞI TẠO HÀNG ĐỢI (QUEUE) ---
# Hàng đợi này đóng vai trò "bộ đệm", giúp Mininet gửi bao nhiêu cũng được,
# Backend sẽ xử lý từ từ mà không bị treo.

MAX_QUEUE_SIZE = 100  # Chỉ cho phép tối đa 100 items trong queue
telemetry_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)

# --- 2. WORKER THREAD (Người tiêu dùng) ---
def db_worker():
    """
    Hàm này chạy vĩnh viễn trong 1 thread riêng.
    Nó liên tục lấy dữ liệu từ queue và ghi vào InfluxDB.
    """
    logger.info(">>> InfluxDB Worker đã khởi động và đang chờ dữ liệu...")
    consecutive_errors = 0  # Đếm số lỗi liên tiếp
    while True:
        # Lấy dữ liệu từ hàng đợi (sẽ block/đứng chờ tại đây nếu hàng đợi rỗng)
        data = telemetry_queue.get()
        
        if data is None: # Tín hiệu dừng (nếu cần tắt server êm đẹp)
            break
        
        # [MỚI] Log kích thước queue mỗi 10 lần ghi
        current_size = telemetry_queue.qsize()
        if current_size > 50:  # Cảnh báo khi queue > 50% capacity
            logger.warning(f"⚠️ Queue đang đầy {current_size}/{MAX_QUEUE_SIZE} items!")
            
        try:
            # Ghi vào DB (Tác vụ tốn thời gian IO)
            influx_service.write_telemetry_batch(data)
            consecutive_errors = 0  # Reset đếm lỗi khi ghi thành công

        except Exception as e:
            logger.error(f"Lỗi ghi InfluxDB background: {e}")
            # Nếu lỗi liên tiếp > 10 lần → InfluxDB có thể đã chết
            if consecutive_errors >= 10:
                logger.critical("🔥 InfluxDB có thể đã ngừng hoạt động! Tạm ngưng ghi 10s...")
                time.sleep(10)  # Ngủ 10s để InfluxDB có cơ hội hồi phục
                consecutive_errors = 0  # Reset
        finally:
            # Đánh dấu là đã xử lý xong item này
            telemetry_queue.task_done()

# --- 3. KHỞI ĐỘNG WORKER ---
# Chỉ chạy 1 lần duy nhất khi file này được import
# daemon=True nghĩa là thread này sẽ tự chết khi chương trình chính tắt
worker_thread = threading.Thread(target=db_worker, daemon=True)
worker_thread.start()

def register_socket_events(socketio):
    """
    Hàm này sẽ được gọi tại Factory để đăng ký các sự kiện WebSocket
    """

    @socketio.on('connect')
    def handle_connect():
        """Xử lý khi client kết nối"""
        logger.info(f"Client connected: {request.sid}")
        
        # Gửi trạng thái ban đầu cho client mới
        snapshot = digital_twin.get_network_snapshot()
        emit('initial_state', snapshot)

    @socketio.on('disconnect')
    def handle_disconnect():
        """Xử lý khi client ngắt kết nối"""
        logger.info(f"Client disconnected: {request.sid}")
    # ========================================
    # ✅ FIX: THÊM HANDLER CHO SWITCH_UPDATED VÀ HOST_UPDATED
    # ========================================
    @socketio.on('switch_updated')
    def handle_switch_update_explicit(data):
        """
        Nhận sự kiện switch_updated trực tiếp từ Mininet (khi toggle)
        Data format: {'name': 's1', 'status': 'offline', 'dpid': ...}
        """
        s_name = data.get('name')
        s_status = data.get('status')
        
        if not s_name:
            logger.warning("[EVENT] switch_updated missing 'name'")
            return

        logger.info(f"⚡ [EVENT] Received explicit switch update: {s_name} → {s_status}")

        with data_lock:
            switch = digital_twin.get_switch(s_name)
            if switch:
                # 1. Cập nhật trạng thái trong Digital Twin (Backend Memory)
                switch.set_status(s_status)
                
                # 2. Broadcast ngay lập tức cho Frontend
                socketio.emit('switch_updated', switch.to_json())
                logger.info(f"✅ [EVENT] Broadcasted switch_updated: {s_name} → {s_status}")
            else:
                logger.warning(f"[EVENT] Switch {s_name} not found in Digital Twin")

    @socketio.on('host_updated')
    def handle_host_update_explicit(data):
        """
        Nhận sự kiện host_updated trực tiếp từ Mininet (khi toggle)
        Data format: {'name': 'h1', 'status': 'offline', ...}
        """
        h_name = data.get('name')
        h_status = data.get('status')
        
        if not h_name:
            logger.warning("[EVENT] host_updated missing 'name'")
            return

        logger.info(f"⚡ [EVENT] Received explicit host update: {h_name} → {h_status}")

        with data_lock:
            host = digital_twin.get_host(h_name)
            if host:
                # 1. Cập nhật trạng thái trong Digital Twin
                host.set_status(h_status)
                
                # 2. Broadcast ngay lập tức cho Frontend
                socketio.emit('host_updated', host.to_json())
                logger.info(f"✅ [EVENT] Broadcasted host_updated: {h_name} → {h_status}")
            else:
                logger.warning(f"[EVENT] Host {h_name} not found in Digital Twin")

    @socketio.on('mininet_telemetry')
    def handle_mininet_telemetry(data):
        # --- A. Đẩy data vào queue (với timeout) ---
        try:
            # Chỉ chờ 0.1 giây, nếu queue đầy thì drop data
            telemetry_queue.put(data, block=True, timeout=0.1)
        except queue.Full:
            # Queue đầy → Không ghi được vào DB → Log cảnh báo
            logger.warning("⚠️ QUEUE ĐẦY! Đã bỏ qua 1 batch dữ liệu để tránh tràn RAM")
            # Không crash, tiếp tục xử lý bình thường
        
        with data_lock:
            batch_timestamp = data.get('timestamp')
            
            # --- B. Cập nhật Digital Twin (từ raw data) ---
            # ========================================
            # ✅ FIX: XỬ LÝ HOST ĐÚNG LOGIC
            # ========================================
            for h_data in data.get('hosts', []):
                host = digital_twin.get_host(h_data['name'])
                if host:
                    # CASE 1: Mininet gửi rõ ràng status=offline
                    if 'status' in h_data and h_data['status'] == 'offline':
                        was_up = (host.status == 'up')
                        host.set_status('offline')
                        
                        # Broadcast ngay lập tức nếu status thay đổi
                        if was_up:
                            socketio.emit('host_updated', host.to_json())
                            logger.info(f"🔴 Host {host.name} → OFFLINE (immediate broadcast)")
                    
                    # CASE 2: Mininet KHÔNG gửi status=offline → Host đang UP
                    # ← ĐÂY LÀ NHÁNH QUAN TRỌNG NHẤT
                    else:
                        was_offline = (host.status == 'offline')
                        
                        # ✅ FIX: Set UP và cập nhật metrics
                        host.set_status('up')
                        host.update_resource_metrics(h_data['cpu'], h_data['mem'], timestamp=batch_timestamp)
                        
                        # ✅ FIX: Nếu host vừa hồi sinh từ offline → Broadcast ngay
                        if was_offline:
                            socketio.emit('host_updated', host.to_json())
                            logger.info(f"🟢 Host {host.name} → UP (recovered from offline)")
            
            for l_data in data.get('links', []):
                parts = l_data['id'].split('-')
                if len(parts) == 2:
                    link = digital_twin.get_link(parts[0], parts[1])
                    if link:
                        previous_status = link.status                       

                        # Cập nhật metrics (hàm này đã tự set status)
                        link.update_performance_metrics(
                            l_data['bw'], 0, timestamp=batch_timestamp
                        )
                        
                        # ========================================
                        # [QUAN TRỌNG] Phát hiện thay đổi status
                        # ========================================
                        if previous_status != link.status:
                            # Status thay đổi → Broadcast ngay lập tức
                            logger.info(f"🔄 Link {link.id} status: {previous_status} → {link.status}")
                            socketio.emit('link_updated', link.to_json())

            # ========================================
            # ✅ FIX: XỬ LÝ SWITCH VỚI STATUS CHECKING V2
            # ========================================
            for s_data in data.get('switches', []):
                # Parse s_data (có thể là string hoặc dict)
                if isinstance(s_data, str):
                    s_name = s_data
                    s_ports = {}
                    s_status = None  # ← Không có status (dữ liệu cũ)
                else:
                    s_name = s_data.get('name')
                    s_ports = s_data.get('ports', {})
                    s_status = s_data.get('status')  # ← Lấy status từ Mininet
                
                switch = digital_twin.get_switch(s_name)
                if switch:
                    previous_status = switch.status  # ← Lưu trạng thái cũ
                    
                    # ========================================
                    # ✅ FIX: LOGIC XỬ LÝ STATUS
                    # ========================================
                    if s_status == 'offline':
                        # CASE 1: Mininet gửi rõ ràng offline
                        switch.set_status('offline')
                        
                        # Broadcast nếu status thay đổi
                        if previous_status != 'offline':
                            socketio.emit('switch_updated', switch.to_json())
                            logger.info(f"🔴 Switch {s_name} → OFFLINE (from Mininet)")
                    
                    elif s_status == 'up':
                        # CASE 2: Mininet gửi rõ ràng up
                        was_offline = (previous_status == 'offline')
                        
                        switch.set_status('up')
                        switch.heartbeat(timestamp=batch_timestamp)
                        if s_ports:
                            switch.update_port_stats(s_ports, timestamp=batch_timestamp)
                        
                        # Broadcast nếu vừa hồi sinh
                        if was_offline:
                            socketio.emit('switch_updated', switch.to_json())
                            logger.info(f"🟢 Switch {s_name} → UP (recovered from offline)")
                    
                    else:
                        # CASE 3: Không có status (dữ liệu cũ) → Chỉ heartbeat
                        # ← KHÔNG đổi status, giữ nguyên
                        switch.heartbeat(timestamp=batch_timestamp)
                        if s_ports:
                            switch.update_port_stats(s_ports, timestamp=batch_timestamp)
                        
                        logger.debug(f"[BATCH] Switch {s_name} heartbeat (status unchanged: {switch.status})")
            
            for item in data.get('latency', []):
                pair_id = item.get('pair')
                latency_val = item.get('latency')
                loss_val = item.get('loss', 0.0)
                jitter_val = item.get('jitter', 0.0)
                
                if pair_id:
                    parts = pair_id.split('-')
                    if len(parts) == 2:
                        src, dst = parts[0], parts[1]
                        digital_twin.update_path_metrics(src, dst, latency_val, loss_val, jitter_val)
            
            # --- C. Tạo SNAPSHOT MỚI từ Digital Twin ---
            # Đây là cách CHUẨN NHẤT: Tạo representation mới từ state hiện tại
            frontend_data = {
                'timestamp': batch_timestamp,
                'hosts': [
                    {
                        'name': h_data['name'],
                        'cpu': h_data['cpu'],
                        'mem': h_data['mem'],
                        'status': digital_twin.get_host(h_data['name']).status
                            if digital_twin.get_host(h_data['name']) else 'unknown'
                    }
                    for h_data in data.get('hosts', [])
                ],
                'links': [
                    {
                        'id': l_data['id'],
                        'bw': l_data['bw'],
                        'status': digital_twin.get_link(
                            l_data['id'].split('-')[0],
                            l_data['id'].split('-')[1]
                        ).status if len(l_data['id'].split('-')) == 2
                            and digital_twin.get_link(
                                l_data['id'].split('-')[0],
                                l_data['id'].split('-')[1]
                            ) else 'unknown'
                    }
                    for l_data in data.get('links', [])
                ],
                # ========================================
                # ✅ FIX: BUILD SWITCHES VỚI STATUS THẬT
                # ========================================
                'switches': [
                    {
                        'name': s_data if isinstance(s_data, str) else s_data.get('name'),
                        'status': digital_twin.get_switch(
                            s_data if isinstance(s_data, str) else s_data.get('name')
                        ).status if digital_twin.get_switch(
                            s_data if isinstance(s_data, str) else s_data.get('name')
                        ) else 'unknown',
                        'ports': s_data.get('ports', {}) if isinstance(s_data, dict) else {}
                    }
                    for s_data in data.get('switches', [])
                ],
                'latency': data.get('latency', [])     # Giữ nguyên
            }
        
        # --- D. Emit snapshot mới ---
        socketio.emit('network_batch_update', frontend_data)
        
        logger.info(f"Đã nhận telemetry từ Mininet: {len(frontend_data['hosts'])} hosts")
    
    # ========================================
    # [MỚI] XỬ LÝ COMMAND RESULT TỪ MININET
    # ========================================
    @socketio.on('command_result')
    def handle_command_result(data):
        """
        Nhận kết quả từ Mininet sau khi thực thi lệnh
        
        Args:
            data (dict): {
                'success': True/False,
                'action_id': 'act_123',
                'command': 'toggle_device',
                'message': 'Success message',
                'error': 'Error message (if failed)',
                'result': {...}  # Dữ liệu kết quả
            }
        """
        action_id = data.get('action_id')
        success = data.get('success', False)
        command = data.get('command')
        error_message = data.get('error')
        result_data = data.get('result')
        
        logger.info(
            f"[CONTROL] Received command result: {action_id} | "
            f"Command: {command} | Success: {success}"
        )
        
        if not action_id:
            logger.warning("[CONTROL] Command result missing action_id")
            return
        
        # Cập nhật Action Log
        if success:
            action_logger_service.update_action(
                action_id=action_id,
                status=ActionStatus.SUCCESS,
                result_data=result_data
            )
            logger.info(f"[CONTROL] Action {action_id} marked as SUCCESS")
        else:
            action_logger_service.update_action(
                action_id=action_id,
                status=ActionStatus.FAILED,
                error_message=error_message
            )
            logger.warning(f"[CONTROL] Action {action_id} marked as FAILED: {error_message}")
        
        # [OPTIONAL] Broadcast result tới Frontend
        # Frontend đã nhận action_completed/action_failed từ ActionLogger
        # Nhưng có thể emit thêm event riêng nếu cần
        socketio.emit('control_result', {
            'action_id': action_id,
            'success': success,
            'command': command,
            'message': data.get('message'),
            'error': error_message,
            'result': result_data
        })

    