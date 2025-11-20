# backend/app/events/socket_events.py
from flask import request
from flask_socketio import emit
from app.extensions import digital_twin, data_lock # Import kho hàng chung
from app.utils.logger import get_logger

logger = get_logger()

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
        """
        Nhận gói tin tổng hợp từ Mininet và cập nhật Digital Twin.
        """
        with data_lock:
            #  Cập nhật Hosts
            for h_data in data.get('hosts', []):
                host = digital_twin.get_host(h_data['name'])
                if host:
                    host.set_status('up') 
                    host.update_resource_metrics(h_data['cpu'], h_data['mem'])
                    h_data['status'] = host.status

            #  Cập nhật Links
            for l_data in data.get('links', []):
                parts = l_data['id'].split('-')
                if len(parts) == 2:
                    link = digital_twin.get_link(parts[0], parts[1])
                    if link:
                        # Nếu link đang down/offline mà có dữ liệu => Hồi sinh
                        if link.status in ['down', 'offline', 'unknown']:
                            link.set_status('up')
                    
                        link.update_performance_metrics(l_data['bw'], 0) 
                        l_data['status'] = link.status

            #  Cập nhật Switches (Heartbeat)
            for s_name in data.get('switches', []):
                switch = digital_twin.get_switch(s_name)
                if switch:
                    switch.heartbeat()
            
        # Broadcast (phát lại) dữ liệu đã xử lý cho Frontend vẽ biểu đồ
        socketio.emit('network_batch_update', data)
        
        logger.info(f"Đã nhận telemetry từ Mininet: {len(data['hosts'])} hosts")