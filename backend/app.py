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

    # --- 1. Thêm Nodes & Links (Giữ nguyên) ---
    mock_twin.add_host('h1', '10.0.0.1', '00:00:00:00:00:01')
    mock_twin.add_host('h2', '10.0.0.2', '00:00:00:00:00:02')
    mock_twin.add_host('h3', '10.0.0.3', '00:00:00:00:00:03')
    mock_twin.add_host('h4', '10.0.0.4', '00:00:00:00:00:04')
    mock_twin.add_switch('s1', '00:00:00:00:01:01')
    mock_twin.add_switch('s2', '00:00:00:00:01:02')
    mock_twin.add_link('h1', 's1', 100)
    mock_twin.add_link('h2', 's1', 100)
    mock_twin.add_link('h3', 's2', 100)
    mock_twin.add_link('h4', 's2', 100)
    mock_twin.add_link('s1', 's2', 1000)

    # --- 3. Cập nhật Số liệu (Đã dọn dẹp) ---

    # Case 1: h1 (CPU 95% -> Tự động 'high-load')
    host_h1 = mock_twin.get_host('h1')
    if host_h1:
        # CHỈ CẦN GỌI HÀM NÀY:
        host_h1.update_resource_metrics(cpu=95.0, memory=90.0)
    
    link_h1_s1 = mock_twin.get_link('h1', 's1')
    if link_h1_s1:
        link_h1_s1.set_status('up') # Link vẫn cần gán 'up' thủ công
        link_h1_s1.update_performance_metrics(throughput=30.0, latency=5)

    # Case 2: h2 (Offline -> Gán thủ công)
    host_h2 = mock_twin.get_host('h2')
    if host_h2:
        # 'offline' là trạng thái đặc biệt, cần gán thủ công
        host_h2.set_status('offline') 
        host_h2.update_resource_metrics(cpu=0, memory=0)
        
    link_h2_s1 = mock_twin.get_link('h2', 's1')
    if link_h2_s1:
        # 'down' là hậu quả của 'offline', gán thủ công
        link_h2_s1.set_status('down')
        link_h2_s1.update_performance_metrics(throughput=0.0, latency=999)

    # Case 3: h3 (CPU 92.5% -> Tự động 'high-load')
    host_h3 = mock_twin.get_host('h3')
    if host_h3:
        # CHỈ CẦN GỌI HÀM NÀY:
        host_h3.update_resource_metrics(cpu=92.5, memory=85.0)
        
    link_h3_s2 = mock_twin.get_link('h3', 's2')
    if link_h3_s2:
        link_h3_s2.set_status('up')
        link_h3_s2.update_performance_metrics(throughput=88.2, latency=15)

    # Case 4: h4 (CPU 1.2% -> Tự động 'up')
    host_h4 = mock_twin.get_host('h4')
    if host_h4:
        # CHỈ CẦN GỌI HÀM NÀY:
        host_h4.update_resource_metrics(cpu=1.2, memory=10.5)
        
    link_h4_s2 = mock_twin.get_link('h4', 's2')
    if link_h4_s2:
        link_h4_s2.set_status('up')
        link_h4_s2.update_performance_metrics(throughput=99, latency=2)
    
    # Case 5: Switches (Vẫn gán 'up' thủ công)
    switch_s1 = mock_twin.get_switch('s1')
    if switch_s1:
        switch_s1.set_status('up')
    switch_s2 = mock_twin.get_switch('s2')
    if switch_s2:
        switch_s2.set_status('up')

    # Link s1-s2
    link_s1_s2 = mock_twin.get_link('s1', 's2')
    if link_s1_s2:
        link_s1_s2.set_status('up')
        link_s1_s2.update_performance_metrics(throughput=93.3, latency=1)

    # --- 4. Trả về Snapshot ---
    snapshot = mock_twin.get_network_snapshot()
    print(f"Trả về snapshot mạng phức tạp: {snapshot['total_hosts']} hosts, {snapshot['total_switches']} switches")

    return jsonify(snapshot)

if __name__ == '__main__':
    # Chạy trên host 0.0.0.0 để có thể truy cập từ bên ngoài nếu cần
    app.run(debug=True, port=5000, host='0.0.0.0')