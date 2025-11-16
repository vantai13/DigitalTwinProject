import time
import requests
import re
import os
import json
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.node import Host, Switch


import collector

# --- CẤU HÌNH ---
# Địa chỉ server Flask (Backend)
API_BASE_URL = "http://localhost:5000/api" 

# Thời gian nghỉ giữa các lần đồng bộ (tính bằng giây)
SYNC_INTERVAL = 2.0 

# --- HÀM GỬI DỮ LIỆU (PUSH FUNCTIONS) ---
def push_host_data_to_api(hostname, cpu_usage, mem_usage):
    """Gửi (POST) dữ liệu metrics của Host lên Flask API."""
    
    
    url = f"{API_BASE_URL}/update/host/{hostname}"
    
    payload = {
        "cpu": cpu_usage,
        "memory": mem_usage
    }
    
    try:
        response = requests.post(url, json=payload, timeout=1.0)
        # Nếu server trả về lỗi (ví dụ 404, 500)
        response.raise_for_status() 
        
    except requests.exceptions.ConnectionError:
        # Bỏ qua lỗi kết nối (vì chúng ta đã xử lý ở vòng lặp chính)
        pass
    except requests.exceptions.RequestException as e:
        # Bắt các lỗi khác (timeout, 404, 500...)
        print(f"[Lỗi API] Không thể đẩy dữ liệu cho {hostname}: {e}")

def push_link_data_to_api(link_id, throughput_mbps):
    """Gửi (POST) dữ liệu metrics của Link lên Flask API."""
    
    # API endpoint chúng ta SẼ TẠO ở Bước 3
    url = f"{API_BASE_URL}/update/link/{link_id}"
    
    payload = {
        "throughput": throughput_mbps,
        "latency": 0.0 # (Bạn có thể thêm logic `ping` để lấy cái này)
    }
    
    try:
        response = requests.post(url, json=payload, timeout=1.0)
        response.raise_for_status() 
    except requests.exceptions.ConnectionError:
        pass
    except requests.exceptions.RequestException as e:
        print(f"[Lỗi API] Không thể đẩy dữ liệu cho {link_id}: {e}")

def push_topology_to_backend(net):
    """
    Gửi toàn bộ topology (hosts, switches, links) từ đối tượng 'net'
    lên Backend để Backend tự động 'mồi' (seed).
    """
    print(">>> Đang thu thập topology từ Mininet để gửi lên Backend...")

    topology_data = {
        "hosts": [],
        "switches": [],
        "links": []
    }

    # 1. Thu thập thông tin tất cả Hosts
    for host in net.hosts:
        topology_data["hosts"].append({
            "name": host.name,
            "ip": host.IP(),  # Lấy IP thật từ Mininet
            "mac": host.MAC()  # Lấy MAC thật từ Mininet
        })

    # 2. Thu thập thông tin tất cả Switches
    for switch in net.switches:
        topology_data["switches"].append({
            "name": switch.name,
            "dpid": switch.dpid
        })

    # 3. Thu thập thông tin tất cả Links
    processed_links = set()  # Tránh trùng lặp (h1-s1 và s1-h1)

    for link in net.links:
        node1_name = link.intf1.node.name
        node2_name = link.intf2.node.name

        # Chuẩn hóa link_id (sắp xếp theo alphabet)
        link_id = "-".join(sorted([node1_name, node2_name]))

        if link_id in processed_links:
            continue
        processed_links.add(link_id)

        # Lấy băng thông (bandwidth) nếu có
        bw = 100  # Mặc định
        if 'bw' in link.intf1.params:
            bw = link.intf1.params['bw']
        elif 'bw' in link.intf2.params:
            bw = link.intf2.params['bw']

        topology_data["links"].append({
            "node1": node1_name,
            "node2": node2_name,
            "bandwidth": bw
        })

    # Gửi POST request
    try:
        url = f"{API_BASE_URL}/init/topology"
        response = requests.post(url, json=topology_data, timeout=3.0)
        response.raise_for_status() # Báo lỗi nếu API trả về 4xx/5xx
        print(f">>> Gửi topology thành công! ({len(topology_data['hosts'])} hosts, {len(topology_data['switches'])} switches, {len(topology_data['links'])} links)")
        return True
    except requests.exceptions.ConnectionError:
        print(f"[LỖI NGHIÊM TRỌNG] Không thể kết nối đến Backend tại {url}.")
        print(">>> Hãy đảm bảo Backend Flask đang chạy!")
        return False
    except Exception as e:
        print(f"[LỖI] Không thể gửi topology: {e}")
        return False

# --- 2. ĐỊNH NGHĨA TOPOLOGY TỪ FILE CẤU HÌNH ---
class ConfigTopo(Topo):
    """
    Một topo động, tự xây dựng dựa trên file topology.json.
    """
    def build(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Xây dựng đường dẫn TUYỆT ĐỐI đến file topology.json
        # (Đi lên 1 cấp '..' từ 'mininet_twin' để đến thư mục gốc dự án)
        config_path = os.path.join(current_dir, '..', 'topology.json')
        config_path = os.path.abspath(config_path) # Đảm bảo đường dẫn là tuyệt đối
        # --- KẾT THÚC SỬA LỖI --
        
        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception as e:
            print(f"[LỖI] Không thể đọc file topology.json: {e}")
            return

        # Dùng dictionary để lưu các node đã tạo, để sau này tìm lại khi tạo link
        host_nodes = {}
        switch_nodes = {}

        # Thêm hosts
        for host in config.get('hosts', []):
            h = self.addHost(host['name'], ip=host['ip'], mac=host.get('mac'))
            host_nodes[host['name']] = h
            
        # Thêm switches
        for switch in config.get('switches', []):
            s = self.addSwitch(switch['name'], dpid=switch.get('dpid'))
            switch_nodes[switch['name']] = s
            
        # Thêm links
        for link in config.get('links', []):
            node1_name = link['from']
            node2_name = link['to']
            
            # Tìm đối tượng node (Host hoặc Switch) từ tên của nó
            node1 = host_nodes.get(node1_name) or switch_nodes.get(node1_name)
            node2 = host_nodes.get(node2_name) or switch_nodes.get(node2_name)
            
            if node1 and node2:
                self.addLink(node1, node2, bw=link.get('bw', 100))
            else:
                print(f"[Lỗi Topo] Không thể tạo link. Node '{node1_name}' hoặc '{node2_name}' không tồn tại.")

# --- HÀM CHÍNH ĐỂ CHẠY ---
def run_simulation():
    setLogLevel('info')
    
    # Khởi tạo mạng
    topo = ConfigTopo()
    net = Mininet(topo=topo)
    net.start()

    # Gửi topology vừa xây dựng lên Backend
    if not push_topology_to_backend(net):
        print("[DỪNG] Không thể 'mồi' topology cho Backend. Dừng mô phỏng.")
        net.stop()
        return

    # Lấy các đối tượng host và link
    h1 = net.get('h1')
    h2 = net.get('h2')
    
    # Khởi động iPerf server trên h2
    print(">>> Khởi động iPerf server trên h2...")
    h2.cmd('iperf -s -u &')  # UDP server, chạy nền (&)
    # (Hoặc dùng TCP: h2.cmd('iperf -s &'))
    
    # Đợi server khởi động
    import time
    time.sleep(1)
    
    # -------------------------------------------------
    # THÊM MỚI: Khởi động iPerf Client trên h1 (tạo traffic liên tục)
    # -------------------------------------------------
    print(">>> Khởi động iPerf client trên h1 (gửi traffic đến h2)...")
    # UDP, 10 Mbps, chạy vô tận (-t 999999 giây)
    h1.cmd('iperf -c 10.0.0.2 -u -b 10M -t 999999 &')
    
   
    
    print(" Mạng Mininet đã khởi động...")
    print("Bắt đầu vòng lặp đồng bộ hóa Digital Twin...")
    
    
    
    try:
        # "Bộ nhớ" để lưu trữ số bytes của lần lặp trước
        link_byte_counters = {}

        collector.list_all_interfaces(h1)
        collector.list_all_interfaces(h2)
        # ---------------------------------------------
        # VÒNG LẶP ĐỒNG BỘ HÓA (THE SYNC LOOP)
        # ---------------------------------------------
        while True:
            
            # Lặp qua tất cả các host trong mạng
            for host in net.hosts:
                # 1. THU THẬP (Collect)
                cpu = collector.get_host_cpu_usage(host)
                mem = collector.get_host_memory_usage(host)
                
                print(f"[{host.name}] CPU: {cpu}% | Mem: {mem}%")
                push_host_data_to_api(host.name, cpu, mem)

            for link in net.links:
                if not link.intf1 or not link.intf2:
                    continue
                
                intf1 = link.intf1
                intf2 = link.intf2
                node1 = intf1.node
                node2 = intf2.node
                
                link_id = "-".join(sorted([node1.name, node2.name]))
                
                # Đo cả 2 phía
                rx1, tx1 = collector.get_interface_bytes(node1, intf1.name)
                rx2, tx2 = collector.get_interface_bytes(node2, intf2.name)
                
                # Lấy giá trị cũ
                prev_tx1, prev_tx2 = link_byte_counters.get(link_id, (0, 0))
                
                # TX của node1 = RX của node2 (và ngược lại)
                # Chọn MAX để tránh mất dữ liệu
                delta_1to2 = tx1 - prev_tx1  # node1 → node2
                delta_2to1 = tx2 - prev_tx2  # node2 → node1
                
                # Tổng lưu lượng
                total_delta = delta_1to2 + delta_2to1
                
                if total_delta < 0:
                    total_delta = 0
                
                throughput_bps = total_delta / SYNC_INTERVAL
                throughput_mbps = round((throughput_bps * 8) / 1_000_000, 2)
                
                print(f"[{link_id}] Bidirectional Throughput: {throughput_mbps} Mbps")
                push_link_data_to_api(link_id, throughput_mbps)
                
                link_byte_counters[link_id] = (tx1, tx2)
        
            
    except KeyboardInterrupt:
        print("\n>>> Đã nhận lệnh dừng (Ctrl+C). Đang dọn dẹp...")
    except requests.exceptions.ConnectionError:
        # Lỗi này xảy ra nếu Flask server CHƯA CHẠY
        print("\n[LỖI] Không thể kết nối đến Backend Flask tại " + API_BASE_URL)
        print(">>> Hãy đảm bảo server Flask đang chạy!")
    finally:
        # Dọn dẹp Mininet
        net.stop()
        print(">>> Mạng Mininet đã dừng.")


if __name__ == '__main__':
    run_simulation()