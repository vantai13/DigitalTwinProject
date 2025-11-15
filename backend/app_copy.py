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
    """
    print("Nhận yêu cầu trạng thái mạng (phiên bản phức tạp)...")

    mock_twin = NetworkModel("Mock Network")


    mock_twin.add_host('h1', '10.0.0.1', '00:00:00:00:00:01')
    mock_twin.add_host('h2', '10.0.0.2', '00:00:00:00:00:02')
    mock_twin.add_host('h3', '10.0.0.3', '00:00:00:00:00:03')
    mock_twin.add_host('h4', '10.0.0.4', '00:00:00:00:00:04')
    # mock_twin.add_host('h5', '10.0.0.5', '00:00:00:00:00:05')
    # mock_twin.add_host('h6', '10.0.0.6', '00:00:00:00:00:06')
    # mock_twin.add_host('h7', '10.0.0.7', '00:00:00:00:00:07')
    # mock_twin.add_host('h8', '10.0.0.8', '00:00:00:00:00:08')
    mock_twin.add_switch('s1', '00:00:00:00:01:01')
    mock_twin.add_switch('s2', '00:00:00:00:01:02')
    mock_twin.add_link('h1', 's1', 100)
    mock_twin.add_link('h2', 's1', 100)
    mock_twin.add_link('h3', 's2', 100)
    mock_twin.add_link('h4', 's2', 100)
    mock_twin.add_link('s1', 's2', 1000)
    # mock_twin.add_link('h5', 'h1', 100)
    # mock_twin.add_link('h6', 's1', 100)
    # mock_twin.add_link('h7', 's2', 100)
    # mock_twin.add_link('h8', 's2', 100)

    host_h1 = mock_twin.get_host('h1')
    if host_h1:
        # CHỈ CẦN GỌI HÀM NÀY:
        host_h1.update_resource_metrics(cpu=95.0, memory=90.0)
    
    link_h1_s1 = mock_twin.get_link('h1', 's1')
    if link_h1_s1:
        link_h1_s1.set_status('up') 
        link_h1_s1.update_performance_metrics(throughput=30.0, latency=5)

    host_h2 = mock_twin.get_host('h2')
    if host_h2:
        host_h2.set_status('offline') 
        host_h2.update_resource_metrics(cpu=0, memory=0)
        
    link_h2_s1 = mock_twin.get_link('h2', 's1')
    if link_h2_s1:
        link_h2_s1.set_status('down')
        link_h2_s1.update_performance_metrics(throughput=0.0, latency=999)

    host_h3 = mock_twin.get_host('h3')
    if host_h3:
        host_h3.update_resource_metrics(cpu=82.5, memory=85.0)
        
    link_h3_s2 = mock_twin.get_link('h3', 's2')
    if link_h3_s2:
        link_h3_s2.set_status('up')
        link_h3_s2.update_performance_metrics(throughput=88.2, latency=15)


    host_h4 = mock_twin.get_host('h4')
    if host_h4:
        host_h4.update_resource_metrics(cpu=1.2, memory=10.5)
        
    link_h4_s2 = mock_twin.get_link('h4', 's2')
    if link_h4_s2:
        link_h4_s2.set_status('up')
        link_h4_s2.update_performance_metrics(throughput=99, latency=2)
    
    switch_s1 = mock_twin.get_switch('s1')
    if switch_s1:
        switch_s1.set_status('up')
    switch_s2 = mock_twin.get_switch('s2')
    if switch_s2:
        switch_s2.set_status('up')

    link_s1_s2 = mock_twin.get_link('s1', 's2')
    if link_s1_s2:
        link_s1_s2.set_status('up')
        link_s1_s2.update_performance_metrics(throughput=93.3, latency=1)

    # h5 = mock_twin.get_host('h5')
    # if h5:
    #     h5.set_status('offline')
    #     h5.update_resource_metrics(cpu=10.0, memory=20.0)

    # link_h1_h5 = mock_twin.get_link('h5', 'h1')
    # if link_h1_h5:
    #     link_h1_h5.set_status('down')
    #     link_h1_h5.update_performance_metrics(throughput=0.0, latency=999)

    # --- 4. Trả về Snapshot ---
    snapshot = mock_twin.get_network_snapshot()
    print(f"Trả về snapshot mạng phức tạp: {snapshot['total_hosts']} hosts, {snapshot['total_switches']} switches")

    return jsonify(snapshot)

if __name__ == '__main__':
    # Chạy trên host 0.0.0.0 để có thể truy cập từ bên ngoài nếu cần
    app.run(debug=True, port=5000, host='0.0.0.0')