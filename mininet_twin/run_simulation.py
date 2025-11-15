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
# Chúng ta sẽ tạo các API này ở Bước 3
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

# # --- ĐỊNH NGHĨA TOPOLOGY ---
# class MySimpleTopo(Topo):
#     def build(self):
        
#         h1 = self.addHost('h1', ip='10.0.0.1/24')
#         h2 = self.addHost('h2', ip='10.0.0.2/24')
        
        
#         s1 = self.addSwitch('s1')
        
        
#         self.addLink(h1, s1, bw=100)
#         self.addLink(h2, s1, bw=100)


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
            # Bỏ qua link chưa sẵn sàng
                if not link.intf1 or not link.intf2:
                    continue
                
                intf1 = link.intf1
                intf2 = link.intf2
                node1 = intf1.node
                node2 = intf2.node
                
                # Chuẩn hóa link_id (alphabet order)
                link_id = "-".join(sorted([node1.name, node2.name]))
                
                # Chỉ xử lý nếu một trong hai node là Host
                host_node = None
                host_intf = None
                if isinstance(node1, Host):
                    host_node = node1
                    host_intf = intf1
                elif isinstance(node2, Host):
                    host_node = node2
                    host_intf = intf2
                else:
                    continue  # Bỏ qua link switch-switch (nếu có)
                
                # Lấy bytes hiện tại
                current_rx, current_tx = collector.get_interface_bytes(host_node, host_intf.name)
                print(f"[DEBUG]   current_tx = {current_tx} bytes")
                
                # Lấy bytes cũ
                prev_rx, prev_tx = link_byte_counters.get(link_id, (0, 0))
                print(f"[DEBUG]   prev_tx = {prev_tx} bytes")
                
                # Tính delta 
                # gửi đi 
                delta_bytes = (current_tx - prev_tx) + (current_rx - prev_rx)
 
                

                if delta_bytes < 0:
                    delta_bytes = 0  # Tránh âm do reset counter
                print(f"[DEBUG]   delta_bytes = {delta_bytes} bytes")
                
                # Tính throughput
                throughput_bps = delta_bytes / SYNC_INTERVAL
                throughput_mbps = round((throughput_bps * 8) / 1_000_000, 2)
                
                print(f"[{link_id}] Throughput: {throughput_mbps} Mbps")
                
                # Gửi API
                push_link_data_to_api(link_id, throughput_mbps)
                
                # Cập nhật bộ nhớ
                link_byte_counters[link_id] = (current_rx, current_tx)

                # --------------------------------------------
                
            # 3. NGHỈ (Sleep)
            time.sleep(SYNC_INTERVAL)
        
            
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