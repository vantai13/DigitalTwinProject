import sys
import os
from flask import Flask, jsonify, request
from flask_cors import CORS



# current_dir = os.path.dirname(os.path.abspath(__file__))
# model_path = os.path.join(current_dir, 'model')
# sys.path.append(model_path)

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
CORS(app) # Cho phép Frontend gọi API

app.logger.info(">>> Khởi tạo 'Bộ não' Digital Twin...")

# TẠO MỘT ĐỐI TƯỢNG DIGITAL TWIN DUY NHẤT (TOÀN CỤC)
digital_twin = NetworkModel("Main Digital Twin")


@app.route('/api/update/host/<hostname>', methods=['POST'])
def update_host_data(hostname):
    """
    API Endpoint để Mininet (collector) cập nhật metrics cho Host.
    """
    
    data = request.get_json(silent=True) or {}
    
    host_obj = digital_twin.get_host(hostname)
    
    if host_obj:
         
        cpu = data.get('cpu', 0.0)
        memory = data.get('memory', 0.0)
        host_obj.update_resource_metrics(cpu, memory)
        
        
        return jsonify({"status": "success", "message": f"{hostname} updated"})
    else:
        # Trả về lỗi 404 nếu Mininet cố update một host không tồn tại
        return jsonify({"status": "error", "message": "Host not found"}), 404

@app.route('/api/update/link/<link_id>', methods=['POST'])
def update_link_data(link_id):
    """
    API Endpoint để Mininet (collector) cập nhật metrics cho Link.
    """
    
    data = request.get_json(silent=True) or {}
    
   
    nodes = link_id.split('-')
    if len(nodes) != 2:
        return jsonify({"status": "error", "message": "Link ID không hợp lệ"}), 400
        
    node1, node2 = nodes[0], nodes[1]
    

    link_obj = digital_twin.get_link(node1, node2)
    
    if link_obj:
        throughput = data.get('throughput', 0.0)
        latency = data.get('latency', 0.0) 
        link_obj.update_performance_metrics(throughput, latency)
        
        # print(f"[API Update] Cập nhật Link {link_id}: Throughput={throughput} Mbps")
        return jsonify({"status": "success", "message": f"{link_id} updated"})
    else:
        return jsonify({"status": "error", "message": "Link not found"}), 404

# (của file run_simulation.py)
print(">>> Đang 'mồi' (seed) topo mạng ban đầu...")
digital_twin.add_host('h1', '10.0.0.1', '00:00:00:00:00:01')
digital_twin.add_host('h2', '10.0.0.2', '00:00:00:00:00:02')
digital_twin.add_switch('s1', '00:00:00:00:01:01')
digital_twin.add_link('h1', 's1', bandwidth_capacity=100) 
digital_twin.add_link('h2', 's1', bandwidth_capacity=100) 

print(">>> 'Bộ não' Digital Twin đã sẵn sàng.")



@app.route('/api/network/status')
def get_network_status():
    """
    API endpoint để Frontend (Vue.js) lấy snapshot MỚI NHẤT
    của toàn bộ mạng.
    """
    print(">>> Nhận yêu cầu [GET /api/network/status] từ Frontend...")
    
    # Chỉ cần gọi hàm get_network_snapshot() từ "bộ não" toàn cục!
    # Không cần tạo mock data nữa.
    snapshot = digital_twin.get_network_snapshot()
    
    print(f"    -> Trả về snapshot: {snapshot['total_hosts']} hosts, {snapshot['total_links']} links.")
    return jsonify(snapshot)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')