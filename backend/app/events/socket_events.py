import threading
from sqlite3.dbapi2 import Timestamp
from flask import request
from flask_socketio import emit
from app.extensions import digital_twin, data_lock # Import kho hàng chung
from app.utils.logger import get_logger
from app.services.influx_service import influx_service
import queue

logger = get_logger()


# --- 1. KHỞI TẠO HÀNG ĐỢI (QUEUE) ---
# Hàng đợi này đóng vai trò "bộ đệm", giúp Mininet gửi bao nhiêu cũng được,
# Backend sẽ xử lý từ từ mà không bị treo.
telemetry_queue = queue.Queue()

# --- 2. WORKER THREAD (Người tiêu dùng) ---
def db_worker():
    """
    Hàm này chạy vĩnh viễn trong 1 thread riêng.
    Nó liên tục lấy dữ liệu từ queue và ghi vào InfluxDB.
    """
    logger.info(">>> InfluxDB Worker đã khởi động và đang chờ dữ liệu...")
    
    while True:
        # Lấy dữ liệu từ hàng đợi (sẽ block/đứng chờ tại đây nếu hàng đợi rỗng)
        data = telemetry_queue.get()
        
        if data is None: # Tín hiệu dừng (nếu cần tắt server êm đẹp)
            break
            
        try:
            # Ghi vào DB (Tác vụ tốn thời gian IO)
            influx_service.write_telemetry_batch(data)
        except Exception as e:
            logger.error(f"Lỗi ghi InfluxDB background: {e}")
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

    @socketio.on('mininet_telemetry')
    def handle_mininet_telemetry(data):
        # --- A. Đẩy data GỐC vào queue ---
        telemetry_queue.put(data)
        
        with data_lock:
            batch_timestamp = data.get('timestamp')
            
            # --- B. Cập nhật Digital Twin (từ raw data) ---
            for h_data in data.get('hosts', []):
                host = digital_twin.get_host(h_data['name'])
                if host:
                    was_offline = (host.status == 'offline')
                    host.set_status('up')
                    host.update_resource_metrics(h_data['cpu'], h_data['mem'], timestamp=batch_timestamp)
                    
                    if was_offline:
                        socketio.emit('host_updated', host.to_json())
            
            for l_data in data.get('links', []):
                parts = l_data['id'].split('-')
                if len(parts) == 2:
                    link = digital_twin.get_link(parts[0], parts[1])
                    if link:
                        if link.status in ['down', 'offline', 'unknown']:
                            link.set_status('up')
                        link.update_performance_metrics(l_data['bw'], 0, timestamp=batch_timestamp)
            
            for s_data in data.get('switches', []):
                if isinstance(s_data, str):
                    s_name = s_data
                    s_ports = {}
                else:
                    s_name = s_data.get('name')
                    s_ports = s_data.get('ports', {})
                
                switch = digital_twin.get_switch(s_name)
                if switch:
                    switch.heartbeat(timestamp=batch_timestamp)
                    if s_ports:
                        switch.update_port_stats(s_ports, timestamp=batch_timestamp)
            
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
                'switches': data.get('switches', []),  # Giữ nguyên
                'latency': data.get('latency', [])     # Giữ nguyên
            }
        
        # --- D. Emit snapshot mới ---
        socketio.emit('network_batch_update', frontend_data)
        
        logger.info(f"Đã nhận telemetry từ Mininet: {len(frontend_data['hosts'])} hosts")