import sys
import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit  # ✅ THÊM SOCKETIO
import threading
from datetime import datetime, timedelta
import time

try:
    from model.host import Host
    from model.switch import Switch
    from model.link import Link
    from model.network_model import NetworkModel
except ImportError as e:
    print(f"Lỗi nghiêm trọng: Không thể import các lớp Model: {e}")
    sys.exit(1)

# ============================================
# KHỞI TẠO FLASK VÀ SOCKETIO
# ============================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # ✅ Cho phép tất cả origins

# ✅ KHỞI TẠO SOCKETIO (QUAN TRỌNG!)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Cho phép mọi origin (development)
    async_mode='threading',     # Chế độ threading
    logger=True,                # Bật logging để debug
    engineio_logger=True
)

# TẠO ĐỐI TƯỢNG DIGITAL TWIN DUY NHẤT
digital_twin = NetworkModel("Main Digital Twin")

# ============================================
# WEBSOCKET EVENT HANDLERS
# ============================================

@socketio.on('connect')
def handle_connect():
    """Xử lý khi client kết nối"""
    print(f"✅ Client connected: {request.sid}")
    
    # Gửi trạng thái ban đầu cho client mới
    snapshot = digital_twin.get_network_snapshot()
    emit('initial_state', snapshot)

@socketio.on('disconnect')
def handle_disconnect():
    """Xử lý khi client ngắt kết nối"""
    print(f"❌ Client disconnected: {request.sid}")

# ============================================
# HELPER FUNCTION: BROADCAST UPDATE
# ============================================

def broadcast_host_update(host_obj):
    """
    Phát (broadcast) cập nhật Host tới TẤT CẢ client đã kết nối.
    """
    socketio.emit('host_updated', host_obj.to_json())

def broadcast_switch_update(switch_obj):
    """
    Phát (broadcast) cập nhật Switch tới TẤT CẢ client đã kết nối.
    """
    socketio.emit('switch_updated', switch_obj.to_json())

def broadcast_link_update(link_obj):
    """
    Phát (broadcast) cập nhật Link tới TẤT CẢ client đã kết nối.
    """
    socketio.emit('link_updated', link_obj.to_json())

# ============================================
# REST API ENDPOINTS (Giữ nguyên như cũ)
# ============================================

@app.route('/api/init/topology', methods=['POST'])
def init_topology():
    """API để Mininet gửi toàn bộ topology lên Backend"""
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    print(">>> Nhận yêu cầu khởi tạo topology từ Mininet...")
    print(f">>> Data nhận được: {json.dumps(data, indent=2)}")

    # Xóa toàn bộ topology cũ
    digital_twin.hosts.clear()
    digital_twin.switches.clear()
    digital_twin.links.clear()

    try:
        # 1. Thêm tất cả Hosts
        for host_data in data.get('hosts', []):
            print(f"[DEBUG] Thêm host: {host_data['name']}")
            digital_twin.add_host(
                host_data['name'],
                host_data['ip'],
                host_data.get('mac', '00:00:00:00:00:00')
            )

        # 2. Thêm tất cả Switches
        for switch_data in data.get('switches', []):
            print(f"[DEBUG] Thêm switch: {switch_data['name']}")
            digital_twin.add_switch(
                switch_data['name'],
                switch_data.get('dpid', '0000000000000001')
            )

        # 3. Thêm tất cả Links
        for link_data in data.get('links', []):
            node1 = link_data['node1']
            node2 = link_data['node2']
            print(f"[DEBUG] Thêm link: {node1} <-> {node2}")
            digital_twin.add_link(
                node1,
                node2,
                link_data.get('bandwidth', 100)
            )

        print(f">>> 'Mồi' topology thành công:")
        print(f"    - {len(digital_twin.hosts)} hosts")
        print(f"    - {len(digital_twin.switches)} switches")
        print(f"    - {len(digital_twin.links)} links")
        
        # ✅ GỬI INITIAL STATE CHO TẤT CẢ CLIENT
        try:
            snapshot = digital_twin.get_network_snapshot()
            socketio.emit('initial_state', snapshot, broadcast=True)
            print(">>> Đã broadcast initial_state qua WebSocket")
        except Exception as emit_error:
            print(f"[CẢNH BÁO] Không thể emit WebSocket: {emit_error}")
        
        return jsonify({"status": "success", "message": "Topology initialized"})
    
    except KeyError as e:
        import traceback
        print(f"[LỖI] Missing key: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Missing key: {e}"}), 400
    except Exception as e:
        import traceback
        print(f"[LỖI] Exception: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Failed: {str(e)}"}), 500


@app.route('/api/update/host/<hostname>', methods=['POST'])
def update_host_data(hostname):
    """API Endpoint để Mininet cập nhật metrics cho Host"""
    data = request.get_json(silent=True) or {}
    host_obj = digital_twin.get_host(hostname)
    
    if not host_obj:
        return jsonify({
            "status": "error", 
            "message": f"Host '{hostname}' không tồn tại"
        }), 404
    
    cpu = data.get('cpu', 0.0)
    memory = data.get('memory', 0.0)
    host_obj.update_resource_metrics(cpu, memory)
    
    # ✅ PHÁT WEBSOCKET EVENT
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
    
    # ✅ PHÁT WEBSOCKET EVENT
    broadcast_link_update(link_obj)
    
    return jsonify({"status": "success", "message": f"{link_id} updated"})


@app.route('/api/update/switch/<switch_name>/heartbeat', methods=['POST'])
def update_switch_heartbeat(switch_name):
    """Nhận tín hiệu 'heartbeat' từ Switch"""
    switch_obj = digital_twin.get_switch(switch_name)
    
    if not switch_obj:
        return jsonify({"status": "error", "message": "Switch not found"}), 404
    
    switch_obj.heartbeat()
    
    # ✅ PHÁT WEBSOCKET EVENT
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
# REAPER THREAD (Giữ nguyên)
# ============================================

def check_device_status_loop():
    """Kiểm tra thiết bị timeout"""
    TIMEOUT_SECONDS = 10.0 
    print(f"⏱️ Kiểm tra thiết bị mỗi 5 giây (Timeout: {TIMEOUT_SECONDS}s)")

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
                            print(f"[Reaper] Host {host.name} timeout → OFFLINE")
                            host.set_status('offline')
                            broadcast_host_update(host)  # ✅ Broadcast

            # Kiểm tra Switches
            for switch in digital_twin.switches.values():
                if switch.last_update_time:
                    if (now - switch.last_update_time) > timeout_threshold:
                        if switch.status != 'offline':
                            print(f"[Reaper] Switch {switch.name} timeout → OFFLINE")
                            switch.set_status('offline')
                            broadcast_switch_update(switch)  # ✅ Broadcast

            # Kiểm tra Links
            for link in digital_twin.links.values():
                if link.last_update_time:
                    if (now - link.last_update_time) > timeout_threshold:
                        if link.status != 'down':
                            print(f"[Reaper] Link {link.id} timeout → DOWN")
                            link.set_status('down')
                            broadcast_link_update(link)  # ✅ Broadcast

        except Exception as e:
            print(f"[Reaper Lỗi] {e}")


reaper_thread = threading.Thread(target=check_device_status_loop, daemon=True)
reaper_thread.start()


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 FLASK BACKEND + SOCKETIO ĐÃ KHỞI ĐỘNG")
    print("="*50)
    print(f"API Base URL: http://0.0.0.0:5000/api")
    print(f"WebSocket URL: ws://0.0.0.0:5000")
    print("="*50 + "\n")
    
    # ✅ CHẠY VỚI SOCKETIO (KHÔNG DÙNG app.run())
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        allow_unsafe_werkzeug=True  # Cho phép chạy trong development
    )