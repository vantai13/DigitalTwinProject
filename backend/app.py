import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir))

try:
    from model.network_model import NetworkModel
except ImportError as e:
    print(f"Error importing NetworkModel: {e}")
    sys.exit(1)

app = Flask(__name__)

# "Cho phép TẤT CẢ các 'origin' (địa chỉ) gọi API."
CORS(app)

# http://127.0.0.1:5000/api/network/status
@app.route('/api/network/status')
def get_network_status():
    """
    API endpoint để lấy trạng thái hiện tại của mạng.
    (Phiên bản phức tạp hơn để test nhiều trường hợp)
    """
    print("Nhận yêu cầu trạng thái mạng (phiên bản phức tạp)...")
    mock_twin = NetworkModel("Mock Network - Complex")

    # --- 1. Thêm Nodes (Hosts & Switches) ---
    
    # Hosts
    mock_twin.add_host('h1', '10.0.0.1', '00:00:00:00:00:01') # Case 1: Normal
    mock_twin.add_host('h2', '10.0.0.2', '00:00:00:00:00:02') # Case 2: Offline
    mock_twin.add_host('h3', '10.0.0.3', '00:00:00:00:00:03') # Case 3: High Load
    mock_twin.add_host('h4', '10.0.0.4', '00:00:00:00:00:04') # Case 4: Idle
    
    # Switches
    mock_twin.add_switch('s1', '00:00:00:00:01:01')
    mock_twin.add_switch('s2', '00:00:00:00:01:02')

    # --- 2. Thêm Links (Kết nối) ---
    
    # Các host/switch đầu tiên
    mock_twin.add_link('h1', 's1', 100) # 100 Mbps capacity
    mock_twin.add_link('h2', 's1', 100)
    
    # Các host/switch mới
    mock_twin.add_link('h3', 's2', 100)
    mock_twin.add_link('h4', 's2', 100)
    
    # Link kết nối 2 switch (backbone)
    mock_twin.add_link('s1', 's2', 1000) # 1 Gbps capacity

    # --- 3. Cập nhật Trạng thái & Số liệu (Các trường hợp test) ---

    # Case 1: h1 (Normal)
    host_h1 = mock_twin.get_host('h1')
    if host_h1:
        # Gán TRỰC TIẾP status để khớp với UI (bỏ qua hàm set_status)
        host_h1.status = 'up' 
        host_h1.update_resource_metrics(cpu=25.0, memory=40.0)
    
    link_h1_s1 = mock_twin.get_link('h1', 's1')
    if link_h1_s1:
        link_h1_s1.update_performance_metrics(throughput=30.0, latency=5)

    # Case 2: h2 (Offline)
    host_h2 = mock_twin.get_host('h2')
    if host_h2:
        # Gán status 'offline' chính xác như UI mong đợi
        host_h2.status = 'offline' 
        host_h2.update_resource_metrics(cpu=0, memory=0)
        
    link_h2_s1 = mock_twin.get_link('h2', 's1')
    if link_h2_s1:
        link_h2_s1.update_performance_metrics(throughput=0.0, latency=999) # Offline link

    # Case 3: h3 (High Load)
    host_h3 = mock_twin.get_host('h3')
    if host_h3:
        # Gán status 'high-load' chính xác như UI mong đợi
        host_h3.status = 'high-load' 
        host_h3.update_resource_metrics(cpu=92.5, memory=85.0) # Tải cao
        
    link_h3_s2 = mock_twin.get_link('h3', 's2')
    if link_h3_s2:
        link_h3_s2.update_performance_metrics(throughput=88.2, latency=15) # Traffic cao

    # Case 4: h4 (Idle)
    host_h4 = mock_twin.get_host('h4')
    if host_h4:
        host_h4.status = 'up'
        host_h4.update_resource_metrics(cpu=1.2, memory=10.5) # Rảnh rỗi
        
    link_h4_s2 = mock_twin.get_link('h4', 's2')
    if link_h4_s2:
        link_h4_s2.update_performance_metrics(throughput=5.1, latency=2)

    # Case 5: Switches (Cho trạng thái 'up' luôn)
    switch_s1 = mock_twin.get_switch('s1')
    if switch_s1:
        switch_s1.status = 'up'

    switch_s2 = mock_twin.get_switch('s2')
    if switch_s2:
        switch_s2.status = 'up'

    # Link s1-s2 (Backbone) - Giả lập tổng traffic từ s2 qua s1
    link_s1_s2 = mock_twin.get_link('s1', 's2')
    if link_s1_s2:
        # (88.2 + 5.1)
        link_s1_s2.update_performance_metrics(throughput=93.3, latency=1) 

    # --- 4. Trả về Snapshot ---
    snapshot = mock_twin.get_network_snapshot()
    print(f"Trả về snapshot mạng phức tạp: {snapshot['total_hosts']} hosts, {snapshot['total_switches']} switches")

    return jsonify(snapshot)

if __name__ == '__main__':
    # Chạy trên host 0.0.0.0 để có thể truy cập từ bên ngoài nếu cần
    app.run(debug=True, port=5000, host='0.0.0.0')