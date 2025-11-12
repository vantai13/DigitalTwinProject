import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir))

try :
    from model.network_model import NetworkModel
except ImportError as e:
    print(f"Error importing NetworkModel: {e}")
    sys.exit(1)

app = Flask(__name__)

# Nó nói với Flask: "Cho phép TẤT CẢ các 'origin' (địa chỉ) gọi API."
CORS(app)

@app.route('/api/network/status')
def get_network_status():
    """
    API endpoint để lấy trạng thái hiện tại của mạng.
    """
    print("Nhận yêu cầu trạng thái mạng...")
    mock_twin = NetworkModel("Mock Network")

    mock_twin.add_host('h1','10.0.0.1', '00:00:00:00:00:01')
    mock_twin.add_host('h2','10.0.0.2', '00:00:00:00:00:02')
    mock_twin.add_switch('s1', '00:00:00:00:01:01')
    mock_twin.add_link('h1', 's1', 100)
    mock_twin.add_link('h2', 's1', 100)

    link_h1_s1 = mock_twin.get_link('h1', 's1')
    if link_h1_s1:
        link_h1_s1.update_performance_metrics(throughput=30.0, latency=5)

    hosts_h1 = mock_twin.get_host('h1')
    if hosts_h1:
        hosts_h1.set_status('up')
        hosts_h1.update_resource_metrics(cpu=25.0, memory=40.0)
    
    host_h2 = mock_twin.get_host('h2')
    if host_h2:
        host_h2.set_status('down')

    snapshot = mock_twin.get_network_snapshot()
    print(f"Trả về snapshot mạng: {snapshot}")

    return jsonify(snapshot)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')