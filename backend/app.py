import sys
import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit 
import threading
from datetime import datetime, timedelta
import time
import logging
from threading import Lock

try:
    from model.host import Host
    from model.switch import Switch
    from model.link import Link
    from model.network_model import NetworkModel
except ImportError as e:
    print(f"Lỗi nghiêm trọng: Không thể import các lớp Model: {e}")
    sys.exit(1)


# ============================================
# CẤU HÌNH LOGGING (Thay thế hoàn toàn print)
# ============================================
# Tạo thư mục logs nếu chưa tồn tại
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/backend.log", encoding='utf-8'),  # Ghi vào thư mục logs
        logging.StreamHandler(sys.stdout)                            # Hiển thị trên console
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# KHỞI TẠO FLASK VÀ SOCKETIO
# ============================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # cho phép các web khác kết nối

# KHỞI TẠO SOCKETIO bọc flask để thêm khả năng websocket
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Cho phép mọi origin (development)
    async_mode='threading',     # Chế độ threading
    logger=True,                # Bật logging để debug
    engineio_logger=True
)

# TẠO ĐỐI TƯỢNG DIGITAL TWIN
digital_twin = NetworkModel("Main Digital Twin")

data_lock = Lock()

# ============================================
# WEBSOCKET EVENT HANDLERS
# ============================================

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


# ============================================
# HELPER FUNCTION: BROADCAST UPDATE
# ============================================

def broadcast_host_update(host_obj):
    """Phát (broadcast) cập nhật Host tới TẤT CẢ client đã kết nối."""
    socketio.emit('host_updated', host_obj.to_json())

def broadcast_switch_update(switch_obj):
    """Phát (broadcast) cập nhật Switch tới TẤT CẢ client đã kết nối."""
    socketio.emit('switch_updated', switch_obj.to_json())

def broadcast_link_update(link_obj):
    """Phát (broadcast) cập nhật Link tới TẤT CẢ client đã kết nối."""
    socketio.emit('link_updated', link_obj.to_json())


# ============================================
# REST API ENDPOINTS 
# ============================================

@app.route('/api/init/topology', methods=['POST'])
def init_topology():
    """API để Mininet gửi toàn bộ topology lên Backend"""
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    logger.info(">>> Nhận yêu cầu khởi tạo topology từ Mininet...")
    logger.info(f">>> Data nhận được: {json.dumps(data, indent=2)}")

    # Xóa toàn bộ topology cũ
    digital_twin.hosts.clear()
    digital_twin.switches.clear()
    digital_twin.links.clear()

    try:
        # Thêm tất cả Hosts
        for host_data in data.get('hosts', []):
            logger.info(f"[DEBUG] Thêm host: {host_data['name']}")
            digital_twin.add_host(
                host_data['name'],
                host_data['ip'],
                host_data.get('mac', '00:00:00:00:00:00')
            )

        # Thêm tất cả Switches
        for switch_data in data.get('switches', []):
            logger.info(f"[DEBUG] Thêm switch: {switch_data['name']}")
            digital_twin.add_switch(
                switch_data['name'],
                switch_data.get('dpid', '0000000000000001')
            )

        # Thêm tất cả Links
        for link_data in data.get('links', []):
            node1 = link_data['node1']
            node2 = link_data['node2']
            logger.info(f"[DEBUG] Thêm link: {node1} <-> {node2}")
            digital_twin.add_link(
                node1,
                node2,
                link_data.get('bandwidth', 100)
            )

        logger.info(f">>> 'Mồi' topology thành công:")
        logger.info(f"    - {len(digital_twin.hosts)} hosts")
        logger.info(f"    - {len(digital_twin.switches)} switches")
        logger.info(f"    - {len(digital_twin.links)} links")
        
        # GỬI INITIAL STATE CHO TẤT CẢ CLIENT
        try:
            snapshot = digital_twin.get_network_snapshot()
            socketio.emit('initial_state', snapshot, broadcast=True)
            logger.info(">>> Đã broadcast initial_state qua WebSocket")
        except Exception as emit_error:
            logger.warning(f"[CẢNH BÁO] Không thể emit WebSocket: {emit_error}")
        
        return jsonify({"status": "success", "message": "Topology initialized"})
    
    except KeyError as e:
        import traceback
        logger.error(f"[LỖI] Missing key: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Missing key: {e}"}), 400
    except Exception as e:
        import traceback
        logger.error(f"[LỖI] Exception: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed: {str(e)}"}), 500


@app.route('/api/update/host/<hostname>', methods=['POST'])
def update_host_data(hostname): 
    """API Endpoint để Mininet cập nhật metrics cho Host"""
    data = request.get_json(silent=True) or {}
    host_obj = digital_twin.get_host(hostname)
    
    with data_lock: 
        host_obj = digital_twin.get_host(hostname)
        if not host_obj:
            return jsonify({"status": "error"}), 404
        
        cpu = data.get('cpu', 0.0)
        memory = data.get('memory', 0.0)
        host_obj.update_resource_metrics(cpu, memory)
        
    # PHÁT WEBSOCKET EVENT
    broadcast_host_update(host_obj)
    
    return jsonify({"status": "success", "message": f"{hostname} updated"})


@app.route('/api/update/link/<link_id>', methods=['POST'])
def update_link_data(link_id):
    """API Endpoint để Mininet cập nhật metrics cho Link"""
    data = request.get_json(silent=True) or {}
    
    nodes = link_id.split('-')
    if len(nodes) != 2:
        return jsonify({
            "status": "error", 
            "message": "Link ID không hợp lệ"
        }), 400
    
    node1, node2 = nodes[0], nodes[1]
    link_obj = digital_twin.get_link(node1, node2)
    
    if not link_obj:
        return jsonify({
            "status": "error", 
            "message": f"Link '{link_id}' không tồn tại"
        }), 404
    
    throughput = data.get('throughput', 0.0)
    latency = data.get('latency', 0.0)
    link_obj.update_performance_metrics(throughput, latency)
    
    # PHÁT WEBSOCKET EVENT
    broadcast_link_update(link_obj)
    
    return jsonify({"status": "success", "message": f"{link_id} updated"})


@app.route('/api/update/switch/<switch_name>/heartbeat', methods=['POST'])
def update_switch_heartbeat(switch_name):
    """Nhận tín hiệu 'heartbeat' từ Switch"""
    switch_obj = digital_twin.get_switch(switch_name)
    
    if not switch_obj:
        return jsonify({"status": "error", "message": "Switch not found"}), 404
    
    switch_obj.heartbeat() # update live switch
    
    broadcast_switch_update(switch_obj)
    
    return jsonify({"status": "success"})


@app.route('/api/network/status')
def get_network_status():
    """API endpoint để Frontend lấy snapshot"""
    snapshot = digital_twin.get_network_snapshot()
    return jsonify(snapshot)


@app.route('/api/health')
def health_check():
    """Kiểm tra server có sống không"""
    return jsonify({
        "status": "healthy",
        "digital_twin": digital_twin.name,
        "hosts": len(digital_twin.hosts),
        "switches": len(digital_twin.switches),
        "links": len(digital_twin.links)
    })


# ============================================
# [MỚI] XỬ LÝ DỮ LIỆU TỪ MININET QUA WEBSOCKET
# ============================================
@socketio.on('mininet_telemetry')
def handle_mininet_telemetry(data):
    """
    Nhận gói tin tổng hợp từ Mininet và cập nhật Digital Twin.
    Dữ liệu data có dạng:
    {
        "hosts": [{"name": "h1", "cpu": 10.5, "mem": 45.2}, ...],
        "links": [{"id": "h1-s1", "bw": 15.5}, ...],
        "switches": ["s1", "s2"]
    }
    """
    with data_lock:
        # 1. Cập nhật Hosts
        for h_data in data.get('hosts', []):
            host = digital_twin.get_host(h_data['name'])
            if host:
                host.update_resource_metrics(h_data['cpu'], h_data['mem'])

        # 2. Cập nhật Links vào Model
        for l_data in data.get('links', []):
            parts = l_data['id'].split('-')
            if len(parts) == 2:
                link = digital_twin.get_link(parts[0], parts[1])
                if link:
                    # 0 là latency (tạm thời)
                    link.update_performance_metrics(l_data['bw'], 0) 

        # 3. Cập nhật Switches (Heartbeat)
        for s_name in data.get('switches', []):
            switch = digital_twin.get_switch(s_name)
            if switch:
                switch.heartbeat()
        
    socketio.emit('network_batch_update', data)

    # (Tùy chọn) In log nhẹ để biết đang nhận tin
    logger.info(f"Đã nhận telemetry từ Mininet: {len(data['hosts'])} hosts")

# ============================================
# REAPER THREAD (Giữ nguyên)
# ============================================

def check_device_status_loop():
    """Kiểm tra thiết bị timeout"""
    TIMEOUT_SECONDS = 10.0 
    logger.info(f" Kiểm tra thiết bị mỗi 5 giây (Timeout: {TIMEOUT_SECONDS}s)")

    while True:
        try:
            time.sleep(5) 
            now = datetime.now()
            timeout_threshold = timedelta(seconds=TIMEOUT_SECONDS)

            # Kiểm tra Hosts
            for host in digital_twin.hosts.values():
                if host.last_update_time:
                    if (now - host.last_update_time) > timeout_threshold:
                        if host.status != 'offline':
                            logger.warning(f"[Reaper] Host {host.name} timeout → OFFLINE")
                            host.set_status('offline')
                            broadcast_host_update(host)

            # Kiểm tra Switches
            for switch in digital_twin.switches.values():
                if switch.last_update_time:
                    if (now - switch.last_update_time) > timeout_threshold:
                        if switch.status != 'offline':
                            logger.warning(f"[Reaper] Switch {switch.name} timeout → OFFLINE")
                            switch.set_status('offline')
                            broadcast_switch_update(switch)

            # Kiểm tra Links
            for link in digital_twin.links.values():
                if link.last_update_time:
                    if (now - link.last_update_time) > timeout_threshold:
                        if link.status != 'down':
                            logger.warning(f"[Reaper] Link {link.id} timeout → DOWN")
                            link.set_status('down')
                            broadcast_link_update(link)

        except Exception as e:
            logger.error(f"[Reaper Lỗi] {e}")


reaper_thread = threading.Thread(target=check_device_status_loop, daemon=True)
reaper_thread.start()


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("FLASK BACKEND + SOCKETIO ĐÃ KHỞI ĐỘNG")
    print("="*50)
    print(f"API Base URL: http://0.0.0.0:5000/api")
    print(f"WebSocket URL: ws://0.0.0.0:5000")
    print("="*50 + "\n")
    
    # CHẠY VỚI SOCKETIO 
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True
    )