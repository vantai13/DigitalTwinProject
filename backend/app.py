import sys
import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from model.host import Host
    from model.switch import Switch
    from model.link import Link
    from model.network_model import NetworkModel
except ImportError as e:
    print(f"Lỗi nghiêm trọng: Không thể import các lớp Model: {e}")
    print("Hãy đảm bảo bạn có các file host.py, link.py, network_model.py...")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

# TẠO ĐỐI TƯỢNG DIGITAL TWIN DUY NHẤT
digital_twin = NetworkModel("Main Digital Twin")

# #  SỬA: Xây dựng đường dẫn đúng
# current_dir = os.path.dirname(os.path.abspath(__file__))
# config_path = os.path.join(current_dir, '..', 'topology.json')
# config_path = os.path.abspath(config_path)

# # KIỂM TRA FILE TỒN TẠI
# if not os.path.exists(config_path):
#     print(f"[LỖI NGHIÊM TRỌNG] Không tìm thấy file topology.json tại '{config_path}'")
#     print("[HƯỚNG DẪN] Hãy tạo file topology.json ở thư mục gốc dự án")
#     sys.exit(1)

# # ĐỌC VÀ PARSE JSON
# try:
#     with open(config_path, 'r', encoding='utf-8') as f:
#         topo_config = json.load(f)
    
#     print(f" Đã load topology.json thành công từ: {config_path}")
    
# except json.JSONDecodeError as e:
#     print(f"[LỖI] File topology.json có lỗi cú pháp JSON: {e}")
#     sys.exit(1)
# except Exception as e:
#     print(f"[LỖI] Không thể đọc file topology.json: {e}")
#     sys.exit(1)


# ============================================
# API ENDPOINTS
# ============================================
@app.route('/api/init/topology', methods=['POST'])
def init_topology():
    """
    API MỚI: Để Mininet gửi toàn bộ topology (hosts, switches, links)
    lên Backend để 'mồi' (seed) tự động.
    """
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    print(">>> Nhận yêu cầu khởi tạo topology từ Mininet...")

    # Xóa toàn bộ topology cũ (để đảm bảo không bị trùng lặp)
    digital_twin.hosts.clear()
    digital_twin.switches.clear()
    digital_twin.links.clear()

    try:
        # 1. Thêm tất cả Hosts
        for host_data in data.get('hosts', []):
            digital_twin.add_host(
                host_data['name'],
                host_data['ip'],
                host_data.get('mac', '00:00:00:00:00:00')
            )

        # 2. Thêm tất cả Switches
        for switch_data in data.get('switches', []):
            digital_twin.add_switch(
                switch_data['name'],
                switch_data.get('dpid', '0000000000000001')
            )

        # 3. Thêm tất cả Links
        for link_data in data.get('links', []):
            digital_twin.add_link(
                link_data['node1'],
                link_data['node2'],
                link_data.get('bandwidth', 100)
            )

        print(f">>> 'Mồi' topology thành công:")
        print(f"    - {len(digital_twin.hosts)} hosts")
        print(f"    - {len(digital_twin.switches)} switches")
        print(f"    - {len(digital_twin.links)} links")
        
        return jsonify({"status": "success", "message": "Topology initialized"})
    
    except KeyError as e:
        # Nếu data gửi lên bị thiếu (ví dụ: host thiếu 'name')
        return jsonify({"status": "error", "message": f"Topology data missing required key: {e}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to build topology: {e}"}), 500

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/update/host/<hostname>', methods=['POST'])
def update_host_data(hostname):
    """API Endpoint để Mininet cập nhật metrics cho Host."""
    data = request.get_json(silent=True) or {}
    host_obj = digital_twin.get_host(hostname)
    
    if not host_obj:
        return jsonify({
            "status": "error", 
            "message": f"Host '{hostname}' không tồn tại trong Digital Twin"
        }), 404
    
    cpu = data.get('cpu', 0.0)
    memory = data.get('memory', 0.0)
    host_obj.update_resource_metrics(cpu, memory)
    
    return jsonify({"status": "success", "message": f"{hostname} updated"})


@app.route('/api/update/link/<link_id>', methods=['POST'])
def update_link_data(link_id):
    """API Endpoint để Mininet cập nhật metrics cho Link."""
    data = request.get_json(silent=True) or {}
    
    # Parse link_id (format: "h1-s1")
    nodes = link_id.split('-')
    if len(nodes) != 2:
        return jsonify({
            "status": "error", 
            "message": "Link ID không hợp lệ (phải có format 'node1-node2')"
        }), 400
    
    node1, node2 = nodes[0], nodes[1]
    link_obj = digital_twin.get_link(node1, node2)
    
    if not link_obj:
        return jsonify({
            "status": "error", 
            "message": f"Link '{link_id}' không tồn tại trong Digital Twin"
        }), 404
    
    throughput = data.get('throughput', 0.0)
    latency = data.get('latency', 0.0)
    link_obj.update_performance_metrics(throughput, latency)
    
    return jsonify({"status": "success", "message": f"{link_id} updated"})


@app.route('/api/network/status')
def get_network_status():
    """API endpoint để Frontend lấy snapshot mới nhất của toàn bộ mạng."""
    snapshot = digital_twin.get_network_snapshot()
    return jsonify(snapshot)


# ============================================
# HEALTH CHECK 
# ============================================
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


if __name__ == '__main__':
    print("\n" + "="*50)
    print("FLASK BACKEND ĐÃ KHỞI ĐỘNG")
    print("="*50)
    print(f"API Base URL: http://0.0.0.0:5000/api")
    print(f"Health Check: http://0.0.0.0:5000/api/health")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')